"""Rotas de clientes (RF01, RF03).

    POST   /api/v1/clients          cadastra empresa cliente
    GET    /api/v1/clients          lista com filtro e paginacao
    GET    /api/v1/clients/{id}     detalha
    PATCH  /api/v1/clients/{id}     edita

Implementa somente POST /api/v1/clients nesta entrega.
"""

from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Response, status
from sqlalchemy.orm import Session

from app.db.session import get_session
from app.repositories.client_repository import ClientRepository
from app.schemas.client import ClientCreate, ClientRead
from app.services.client_service import ClientCnpjConflictError, ClientService

router = APIRouter(prefix="/clients", tags=["clients"])


@router.post("", response_model=ClientRead, status_code=status.HTTP_201_CREATED)
def create_client(
    payload: ClientCreate,
    response: Response,
    session: Annotated[Session, Depends(get_session)],
) -> ClientRead:
    service = ClientService(ClientRepository(session))
    try:
        client = service.create(payload)
    except ClientCnpjConflictError as exc:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(exc)) from exc

    response.headers["Location"] = f"/api/v1/clients/{client.id}"
    return ClientRead.model_validate(client)
