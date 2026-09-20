"""Criacao e consulta filtrada de negociacoes (RF02, RF03)."""

from collections.abc import Callable, Coroutine
from datetime import datetime
from typing import Annotated, Any
from uuid import UUID

from fastapi import APIRouter, Depends, Query, Request, status
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse, Response
from fastapi.routing import APIRoute
from sqlalchemy.orm import Session

from app.db.session import get_session
from app.domain.enums import DemandStatus, PipelineStage
from app.repositories.demand_repository import DemandRepository
from app.schemas.common import PaginatedResponse
from app.schemas.demand import (
    DemandCreate,
    DemandDetail,
    DemandErrorResponse,
    DemandRead,
    DemandUpdate,
)
from app.services.demand_service import DemandCreationError, DemandNotFoundError, DemandService


def _error_response(
    request: Request, status_code: int, code: str, message: str, details: dict[str, str]
) -> JSONResponse:
    error = DemandErrorResponse(
        error={
            "code": code,
            "message": message,
            "details": details,
            "request_id": request.headers.get("X-Request-ID"),
        }
    )
    return JSONResponse(status_code=status_code, content=error.model_dump(exclude_none=True))


class DemandRoute(APIRoute):
    """Aplica o envelope de validacao sem alterar os handlers de outras tasks."""

    def get_route_handler(self) -> Callable[[Request], Coroutine[Any, Any, Response]]:
        original_handler = super().get_route_handler()

        async def handler(request: Request) -> Response:
            try:
                return await original_handler(request)
            except RequestValidationError as exc:
                return _error_response(
                    request,
                    422,
                    "VALIDATION_ERROR",
                    "Dados invalidos para a demanda.",
                    {".".join(map(str, error["loc"])): error["msg"] for error in exc.errors()},
                )

        return handler


router = APIRouter(prefix="/demands", tags=["demands"], route_class=DemandRoute)


@router.get(
    "",
    response_model=PaginatedResponse[DemandRead],
    summary="Listar e filtrar demandas",
    description=(
        "Lista demandas por cliente, etapa, responsavel, periodo de criacao e situacao. "
        "Os filtros informados sao combinados com AND."
    ),
    responses={
        422: {"model": DemandErrorResponse, "description": "Filtros invalidos."},
    },
)
def list_demands(
    request: Request,
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
) -> PaginatedResponse[DemandRead] | JSONResponse:
    """Aplica filtros combinaveis e devolve o total antes da paginacao."""

    period_error = _validate_period(created_from, created_to)
    if period_error is not None:
        return _error_response(
            request,
            422,
            "VALIDATION_ERROR",
            "Periodo de criacao invalido.",
            period_error,
        )

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


def _validate_period(
    created_from: datetime | None, created_to: datetime | None
) -> dict[str, str] | None:
    """Exige fuso e uma faixa cronologica coerente para o filtro de periodo."""

    errors: dict[str, str] = {}
    if created_from is not None and created_from.utcoffset() is None:
        errors["query.from"] = "A data inicial deve informar o fuso horario."
    if created_to is not None and created_to.utcoffset() is None:
        errors["query.to"] = "A data final deve informar o fuso horario."
    if (
        not errors
        and created_from is not None
        and created_to is not None
        and created_from > created_to
    ):
        errors["query.to"] = "A data final deve ser maior ou igual a data inicial."
    return errors or None


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
        404: {"model": DemandErrorResponse, "description": "Cliente ou responsavel inexistente."},
        409: {
            "model": DemandErrorResponse,
            "description": "Referencia removida durante a criacao.",
        },
        422: {"model": DemandErrorResponse, "description": "Dados de entrada invalidos."},
    },
)
def create_demand(
    data: DemandCreate,
    request: Request,
    session: Annotated[Session, Depends(get_session)],
) -> DemandRead | JSONResponse:
    """Aplica o caso de uso e traduz apenas erros previsiveis do dominio."""

    try:
        demand = DemandService(session).create(data)
    except DemandCreationError as exc:
        return _error_response(request, exc.status_code, exc.code, exc.message, exc.details)

    return DemandRead.model_validate(demand)


@router.get(
    "/{demand_id}",
    response_model=DemandDetail,
    summary="Consultar contexto da demanda",
    description=(
        "Retorna o contexto da demanda, o cliente, a etapa corrente e os artefatos "
        "vinculados com suas versoes."
    ),
    responses={
        404: {"model": DemandErrorResponse, "description": "Demanda inexistente."},
        422: {"model": DemandErrorResponse, "description": "Identificador invalido."},
    },
)
def get_demand(
    demand_id: UUID,
    request: Request,
    session: Annotated[Session, Depends(get_session)],
) -> DemandDetail | JSONResponse:
    try:
        demand = DemandService(session).get(demand_id)
    except DemandNotFoundError as exc:
        return _error_response(request, exc.status_code, exc.code, exc.message, exc.details)
    return DemandDetail.model_validate(demand)


@router.patch(
    "/{demand_id}",
    response_model=DemandDetail,
    summary="Editar contexto da demanda",
    description=(
        "Altera somente os campos enviados. description e owner_id enviados como null sao limpos; "
        "etapa, situacao, cliente e artefatos permanecem inalterados."
    ),
    responses={
        404: {"model": DemandErrorResponse, "description": "Demanda ou responsavel inexistente."},
        422: {"model": DemandErrorResponse, "description": "Dados de entrada invalidos."},
    },
)
def update_demand(
    demand_id: UUID,
    data: DemandUpdate,
    request: Request,
    session: Annotated[Session, Depends(get_session)],
) -> DemandDetail | JSONResponse:
    try:
        demand = DemandService(session).update(demand_id, data)
    except (DemandNotFoundError, DemandCreationError) as exc:
        return _error_response(request, exc.status_code, exc.code, exc.message, exc.details)
    return DemandDetail.model_validate(demand)
