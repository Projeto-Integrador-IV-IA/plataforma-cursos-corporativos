"""Rotas do pipeline.

    GET  /api/v1/pipeline                   demandas agrupadas por etapa (RF05)

Movimentacao e historico continuam pendentes e sao outros cards:

    POST /api/v1/demands/{id}/transitions   move de etapa (RF06)
    GET  /api/v1/demands/{id}/transitions   historico completo (RF07)

O corpo da transicao carrega etapa de destino e motivo; o autor vem do token
autenticado, nunca do corpo da requisicao (RNF10).

TODO(RF06, RF07): implementar as rotas de transicao conforme o contrato.
"""

from datetime import datetime
from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.api.v1._validation import validate_period
from app.core.exceptions import ValidationError, issue_de_validacao
from app.db.session import get_session
from app.domain.enums import DemandStatus
from app.schemas.error import ErrorResponse
from app.schemas.pipeline import PipelineBoard
from app.services.pipeline_service import DEFAULT_CARDS_PER_STAGE, PipelineService

router = APIRouter(prefix="/pipeline", tags=["pipeline"])


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
