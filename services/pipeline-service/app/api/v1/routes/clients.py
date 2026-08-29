"""Rotas de clientes (RF01, RF03).

    POST   /api/v1/clients          cadastra empresa cliente
    GET    /api/v1/clients          lista com filtro e paginacao
    GET    /api/v1/clients/{id}     detalha
    PATCH  /api/v1/clients/{id}     edita (fora do escopo da RF01.1)

Implementa cadastro, listagem paginada e consulta por identificador (RF01.1).
"""

import uuid
from typing import Annotated

from fastapi import APIRouter, Depends, Query, Response, status
from sqlalchemy.orm import Session

from app.db.session import get_session
from app.repositories.client_repository import ClientRepository
from app.schemas.client import ClientCreate, ClientPage, ClientRead
from app.schemas.error import ErrorResponse
from app.services.client_service import ClientService

router = APIRouter(prefix="/clients", tags=["clients"])


def get_client_service(session: Annotated[Session, Depends(get_session)]) -> ClientService:
    return ClientService(ClientRepository(session))


@router.post(
    "",
    response_model=ClientRead,
    status_code=status.HTTP_201_CREATED,
    responses={
        status.HTTP_409_CONFLICT: {"model": ErrorResponse},
        422: {"model": ErrorResponse},
    },
)
def create_client(
    payload: ClientCreate,
    response: Response,
    service: Annotated[ClientService, Depends(get_client_service)],
) -> ClientRead:
    client = service.create(payload)
    response.headers["Location"] = f"/api/v1/clients/{client.id}"
    return ClientRead.model_validate(client)


@router.get(
    "",
    response_model=ClientPage,
    responses={422: {"model": ErrorResponse}},
)
def list_clients(
    service: Annotated[ClientService, Depends(get_client_service)],
    page: Annotated[int, Query(ge=1)] = 1,
    size: Annotated[int, Query(ge=1, le=100)] = 20,
) -> ClientPage:
    return service.list(page=page, size=size)


@router.get(
    "/{client_id}",
    response_model=ClientRead,
    responses={
        status.HTTP_404_NOT_FOUND: {"model": ErrorResponse},
        422: {"model": ErrorResponse},
    },
)
def get_client(
    client_id: uuid.UUID,
    service: Annotated[ClientService, Depends(get_client_service)],
) -> ClientRead:
    return ClientRead.model_validate(service.get(client_id))
