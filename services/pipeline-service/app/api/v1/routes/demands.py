"""Criacao e consulta filtrada de negociacoes (RF02, RF03).

Erro nenhum e traduzido aqui: o servico levanta ``PlatformError`` e os handlers
registrados em ``app.core.exceptions`` devolvem o envelope unico da plataforma
(RNF02). Antes existia uma traducao local nesta rota, e o servico respondia
``422`` em dois formatos conforme o caminho.
"""

from datetime import datetime
from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, Query, status
from sqlalchemy.orm import Session

from app.core.exceptions import ValidationError, issue_de_validacao
from app.db.session import get_session
from app.domain.enums import DemandStatus, PipelineStage
from app.repositories.demand_repository import DemandRepository
from app.schemas.common import PaginatedResponse
from app.schemas.demand import (
    DemandCreate,
    DemandDetail,
    DemandRead,
    DemandUpdate,
)
from app.schemas.error import ErrorResponse
from app.services.demand_service import DemandService

router = APIRouter(prefix="/demands", tags=["demands"])


@router.get(
    "",
    response_model=PaginatedResponse[DemandRead],
    summary="Listar e filtrar demandas",
    description=(
        "Lista demandas por cliente, etapa, responsavel, periodo de criacao e situacao. "
        "Os filtros informados sao combinados com AND."
    ),
    responses={
        422: {"model": ErrorResponse, "description": "Filtros invalidos."},
    },
)
def list_demands(
    session: Annotated[Session, Depends(get_session)],
    client_id: UUID | None = None,
    stage: PipelineStage | None = None,
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
    limit: Annotated[int, Query(ge=1, le=100)] = 20,
    offset: Annotated[int, Query(ge=0)] = 0,
) -> PaginatedResponse[DemandRead]:
    """Aplica filtros combinaveis e devolve o total antes da paginacao."""

    _validate_period(created_from, created_to)

    items, total = DemandRepository(session).list(
        client_id=client_id,
        stage=stage,
        owner_id=owner_id,
        created_from=created_from,
        created_to=created_to,
        status=demand_status,
        limit=limit,
        offset=offset,
    )
    return PaginatedResponse[DemandRead](
        items=[DemandRead.model_validate(item) for item in items],
        total=total,
        page=(offset // limit) + 1,
        size=limit,
    )


def _validate_period(created_from: datetime | None, created_to: datetime | None) -> None:
    """Exige fuso e uma faixa cronologica coerente para o filtro de periodo.

    Levanta ``ValidationError`` para que a resposta saia pelo mesmo handler do
    restante do servico, com o ``details.issues`` de sempre.
    """

    issues: list[dict[str, object]] = []
    if created_from is not None and created_from.utcoffset() is None:
        issues.append(
            issue_de_validacao(
                localizacao=["query", "from"],
                mensagem="A data inicial deve informar o fuso horario.",
                tipo="value_error.timezone",
            )
        )
    if created_to is not None and created_to.utcoffset() is None:
        issues.append(
            issue_de_validacao(
                localizacao=["query", "to"],
                mensagem="A data final deve informar o fuso horario.",
                tipo="value_error.timezone",
            )
        )
    if (
        not issues
        and created_from is not None
        and created_to is not None
        and created_from > created_to
    ):
        issues.append(
            issue_de_validacao(
                localizacao=["query", "to"],
                mensagem="A data final deve ser maior ou igual a data inicial.",
                tipo="value_error.period",
            )
        )

    if issues:
        raise ValidationError(
            code="VALIDATION_ERROR",
            message="Os dados informados sao invalidos.",
            details={"issues": issues},
        )


@router.post(
    "",
    response_model=DemandRead,
    status_code=status.HTTP_201_CREATED,
    summary="Criar demanda vinculada a cliente",
    description=(
        "Cria uma negociacao com cliente obrigatorio, na situacao ABERTA e etapa CAPTACAO. "
        "description registra o contexto; owner_id indica um usuario responsavel existente."
    ),
    responses={
        404: {"model": ErrorResponse, "description": "Cliente ou responsavel inexistente."},
        409: {
            "model": ErrorResponse,
            "description": "Referencia removida durante a criacao.",
        },
        422: {"model": ErrorResponse, "description": "Dados de entrada invalidos."},
    },
)
def create_demand(
    data: DemandCreate,
    session: Annotated[Session, Depends(get_session)],
) -> DemandRead:
    """Aplica o caso de uso e traduz apenas erros previsiveis do dominio."""

    return DemandRead.model_validate(DemandService(session).create(data))


@router.get(
    "/{demand_id}",
    response_model=DemandDetail,
    summary="Consultar contexto da demanda",
    description=(
        "Retorna o contexto da demanda, o cliente, a etapa corrente e os artefatos "
        "vinculados com suas versoes."
    ),
    responses={
        404: {"model": ErrorResponse, "description": "Demanda inexistente."},
        422: {"model": ErrorResponse, "description": "Identificador invalido."},
    },
)
def get_demand(
    demand_id: UUID,
    session: Annotated[Session, Depends(get_session)],
) -> DemandDetail:
    return DemandDetail.model_validate(DemandService(session).get(demand_id))


@router.patch(
    "/{demand_id}",
    response_model=DemandDetail,
    summary="Editar contexto da demanda",
    description=(
        "Altera somente os campos enviados. description e owner_id enviados como null sao limpos; "
        "etapa, situacao, cliente e artefatos permanecem inalterados."
    ),
    responses={
        404: {"model": ErrorResponse, "description": "Demanda ou responsavel inexistente."},
        422: {"model": ErrorResponse, "description": "Dados de entrada invalidos."},
    },
)
def update_demand(
    demand_id: UUID,
    data: DemandUpdate,
    session: Annotated[Session, Depends(get_session)],
) -> DemandDetail:
    return DemandDetail.model_validate(DemandService(session).update(demand_id, data))
