"""Rotas do pipeline.

    GET  /api/v1/pipeline                   demandas agrupadas por etapa (RF05)
    POST /api/v1/demands/{id}/advance       avanca para a proxima etapa (RF06)
    GET  /api/v1/demands/{id}/transitions   linha do tempo de etapas (RF07)

O retrocesso continua pendente e e outro card:

    POST /api/v1/demands/{id}/transitions   retrocede de etapa (RF06)

O avanco nao recebe destino: a proxima etapa sai da maquina de estados. O autor
vem do cabecalho ``X-User-ID``, nunca do corpo da requisicao (RNF10) - o mesmo
padrao de ``routes/ingestion.py`` no ingestion-service.

TODO(RF06): implementar o retrocesso conforme o contrato.
"""

from datetime import datetime
from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, Header, Query
from sqlalchemy.orm import Session

from app.api.v1._validation import validate_period
from app.core.exceptions import ValidationError, issue_de_validacao
from app.db.session import get_session
from app.domain.enums import DemandStatus
from app.schemas.error import ErrorResponse
from app.schemas.pipeline import (
    PipelineBoard,
    StageChangeRead,
    StageChangeRequest,
    StageTransitionTimeline,
)
from app.services.pipeline_service import DEFAULT_CARDS_PER_STAGE, PipelineService

router = APIRouter(prefix="/pipeline", tags=["pipeline"])

# O avanco e uma acao sobre a demanda, entao mora em /demands/{id}/..., e nao
# sob /pipeline. Este roteador precisa ser incluido junto com ``router``.
demands_router = APIRouter(prefix="/demands", tags=["pipeline"])


@router.get(
    "",
    response_model=PipelineBoard,
    summary="Consultar demandas agrupadas por etapa",
    description=(
        "Devolve as cinco etapas do pipeline, cada uma com os cartoes da etapa e o total de "
        "demandas que a atendem. As etapas vazias tambem vem, porque o quadro tem colunas "
        "fixas. Aceita os mesmos filtros da listagem de demandas, combinados com AND; o "
        "filtro por etapa nao se aplica aqui, ja que o agrupamento e por etapa."
    ),
    responses={
        422: {"model": ErrorResponse, "description": "Filtros invalidos."},
    },
)
def get_pipeline_board(
    session: Annotated[Session, Depends(get_session)],
    client_id: UUID | None = None,
    owner_id: UUID | None = None,
    created_from: Annotated[
        datetime | None,
        Query(alias="from", description="Inicio inclusivo do periodo de criacao, com fuso."),
    ] = None,
    created_to: Annotated[
        datetime | None,
        Query(alias="to", description="Fim inclusivo do periodo de criacao, com fuso."),
    ] = None,
    demand_status: Annotated[
        DemandStatus | None,
        Query(alias="status", description="Situacao atual da demanda."),
    ] = None,
    limit: Annotated[
        int,
        Query(ge=1, le=100, description="Cartoes trazidos por etapa; o total nao e afetado."),
    ] = DEFAULT_CARDS_PER_STAGE,
    stage: Annotated[
        str | None,
        Query(
            description=(
                "Nao aceito aqui: o agrupamento ja e por etapa. Para uma etapa so, use "
                "GET /api/v1/demands?stage=."
            ),
            deprecated=True,
        ),
    ] = None,
) -> PipelineBoard:
    """Monta o quadro respeitando os filtros ja definidos para a listagem (RF03)."""

    _reject_stage_filter(stage)
    validate_period(created_from, created_to)

    return PipelineService(session).board(
        client_id=client_id,
        owner_id=owner_id,
        created_from=created_from,
        created_to=created_to,
        status=demand_status,
        limit=limit,
    )


def _reject_stage_filter(stage: str | None) -> None:
    """Recusa ``stage`` em vez de ignora-lo em silencio.

    Sem isto o FastAPI descartaria o parametro desconhecido e devolveria o
    quadro inteiro com cara de filtrado - o mesmo engano de um filtro que
    parece aplicado e nao esta. Uma etapa isolada ja tem caminho proprio na
    listagem de demandas (RF03).
    """

    if stage is None:
        return

    raise ValidationError(
        code="VALIDATION_ERROR",
        message="Os dados informados sao invalidos.",
        details={
            "issues": [
                issue_de_validacao(
                    localizacao=["query", "stage"],
                    mensagem=(
                        "A visao de pipeline ja agrupa por etapa. Para consultar uma etapa "
                        "isolada, use GET /api/v1/demands?stage=."
                    ),
                    tipo="value_error.unsupported_filter",
                )
            ]
        },
    )


@demands_router.post(
    "/{demand_id}/advance",
    response_model=StageChangeRead,
    summary="Avancar demanda para a proxima etapa",
    description=(
        "Move a demanda para a etapa seguinte do pipeline e registra a transicao na trilha, "
        "na mesma transacao. O destino e definido pela maquina de estados, nao pelo chamador. "
        "O autor vem do cabecalho X-User-ID. A justificativa e opcional."
    ),
    responses={
        404: {"model": ErrorResponse, "description": "Demanda ou operador inexistente."},
        409: {
            "model": ErrorResponse,
            "description": "Demanda na ultima etapa ou encerrada.",
        },
        422: {"model": ErrorResponse, "description": "Identificador ou justificativa invalidos."},
    },
)
def advance_demand(
    demand_id: UUID,
    author_id: Annotated[UUID, Header(alias="X-User-ID")],
    session: Annotated[Session, Depends(get_session)],
    payload: StageChangeRequest | None = None,
) -> StageChangeRead:
    """Delega ao servico; commit ou rollback ficam com a sessao da requisicao."""

    return PipelineService(session).advance(
        demand_id,
        author_id,
        reason=payload.reason if payload is not None else None,
    )


@demands_router.get(
    "/{demand_id}/transitions",
    response_model=StageTransitionTimeline,
    summary="Consultar a linha do tempo de etapas da demanda",
    description=(
        "Devolve todas as mudancas de etapa da demanda, da mais antiga a mais recente: "
        "etapa de origem, etapa de destino, autor, justificativa e instante. Demanda sem "
        "movimentacao devolve lista vazia."
    ),
    responses={
        404: {"model": ErrorResponse, "description": "Demanda inexistente."},
        422: {"model": ErrorResponse, "description": "Identificador invalido."},
    },
)
def get_demand_timeline(
    demand_id: UUID,
    session: Annotated[Session, Depends(get_session)],
) -> StageTransitionTimeline:
    """Leitura da trilha; nao altera nada e nao exige o cabecalho de autor."""

    return PipelineService(session).timeline(demand_id)
