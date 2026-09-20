"""Criacao de negociacoes vinculadas a clientes (RF02)."""

from collections.abc import Callable, Coroutine
from typing import Annotated, Any
from uuid import UUID

from fastapi import APIRouter, Depends, Request, status
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse, Response
from fastapi.routing import APIRoute
from sqlalchemy.orm import Session

from app.db.session import get_session
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
                    "Dados invalidos para criar a demanda.",
                    {".".join(map(str, error["loc"])): error["msg"] for error in exc.errors()},
                )

        return handler


router = APIRouter(prefix="/demands", tags=["demands"], route_class=DemandRoute)


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
