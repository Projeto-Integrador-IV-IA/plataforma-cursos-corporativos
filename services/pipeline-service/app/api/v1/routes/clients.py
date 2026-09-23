"""Cadastro, consulta e edicao parcial de clientes (RF01.1 e RF01.2)."""

from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, Query, Response, status
from sqlalchemy.orm import Session

from app.db.session import get_session
from app.repositories.client_repository import ClientRepository
from app.schemas.client import ClientCreate, ClientPage, ClientRead, ClientUpdate
from app.schemas.error import ErrorResponse
from app.services.client_service import ClientService

router = APIRouter(prefix="/clients", tags=["clients"])


def get_client_service(session: Annotated[Session, Depends(get_session)]) -> ClientService:
    return ClientService(ClientRepository(session))


@router.post(
    "",
    response_model=ClientRead,
    status_code=status.HTTP_201_CREATED,
    summary="Cadastrar cliente",
    description="Cadastra a identificacao, os contatos e o segmento de uma empresa cliente.",
    responses={
        status.HTTP_409_CONFLICT: {"model": ErrorResponse, "description": "CNPJ duplicado."},
        status.HTTP_422_UNPROCESSABLE_CONTENT: {
            "model": ErrorResponse,
            "description": "Dados de entrada invalidos.",
        },
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
    summary="Listar clientes",
    description="Lista clientes com paginacao deterministica.",
    responses={
        status.HTTP_422_UNPROCESSABLE_CONTENT: {
            "model": ErrorResponse,
            "description": "Paginacao invalida.",
        }
    },
)
def list_clients(
    service: Annotated[ClientService, Depends(get_client_service)],
    page: Annotated[int, Query(ge=1, description="Pagina iniciada em 1.")] = 1,
    size: Annotated[int, Query(ge=1, le=100, description="Itens por pagina.")] = 20,
) -> ClientPage:
    return service.list(page=page, size=size)


@router.get(
    "/{client_id}",
    response_model=ClientRead,
    summary="Consultar cliente por identificador",
    description="Retorna os dados cadastrais usados pela tela de detalhe do cliente.",
    responses={
        status.HTTP_404_NOT_FOUND: {
            "model": ErrorResponse,
            "description": "Cliente inexistente.",
        },
        status.HTTP_422_UNPROCESSABLE_CONTENT: {
            "model": ErrorResponse,
            "description": "Identificador invalido.",
        },
    },
)
def get_client(
    client_id: UUID,
    service: Annotated[ClientService, Depends(get_client_service)],
) -> ClientRead:
    return ClientRead.model_validate(service.get(client_id))


@router.patch(
    "/{client_id}",
    response_model=ClientRead,
    summary="Editar dados de um cliente",
    description=(
        "Altera somente os campos enviados. Campos opcionais enviados como null sao limpos; "
        "a inativacao pertence ao RF01.3 e nao e realizada por esta operacao."
    ),
    responses={
        status.HTTP_404_NOT_FOUND: {
            "model": ErrorResponse,
            "description": "Cliente inexistente.",
        },
        status.HTTP_409_CONFLICT: {"model": ErrorResponse, "description": "CNPJ duplicado."},
        status.HTTP_422_UNPROCESSABLE_CONTENT: {
            "model": ErrorResponse,
            "description": "Dados de entrada invalidos.",
        },
    },
)
def update_client(
    client_id: UUID,
    payload: ClientUpdate,
    service: Annotated[ClientService, Depends(get_client_service)],
) -> ClientRead:
    return ClientRead.model_validate(service.update(client_id, payload))
