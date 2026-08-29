"""Caso de uso: gestao de clientes (RF01, RF03).

Regras: nome corporativo obrigatorio e unico por CNPJ quando informado;
cliente com demandas ativas nao pode ser removido.

Implementa os casos de uso da RF01.1.
"""

import uuid

from sqlalchemy.exc import IntegrityError

from app.core.exceptions import ConflictError, NotFoundError
from app.models.client import Client
from app.repositories.client_repository import ClientRepository
from app.schemas.client import ClientCreate, ClientPage, ClientRead


class ClientService:
    def __init__(self, repository: ClientRepository) -> None:
        self.repository = repository

    def create(self, data: ClientCreate) -> Client:
        if data.cnpj and self.repository.get_by_cnpj(data.cnpj):
            raise self._cnpj_conflict()
        try:
            return self.repository.create(data)
        except IntegrityError as exc:
            self.repository.rollback()
            raise self._cnpj_conflict() from exc

    def get(self, client_id: uuid.UUID) -> Client:
        client = self.repository.get_by_id(client_id)
        if client is None:
            raise NotFoundError(
                code="CLIENT_NOT_FOUND",
                message="Cliente não encontrado.",
                details={"client_id": str(client_id)},
            )
        return client

    def list(self, *, page: int, size: int) -> ClientPage:
        clients, total = self.repository.list(page=page, size=size)
        return ClientPage(
            items=[ClientRead.model_validate(client) for client in clients],
            total=total,
            page=page,
            size=size,
        )

    @staticmethod
    def _cnpj_conflict() -> ConflictError:
        return ConflictError(
            code="CLIENT_CNPJ_ALREADY_EXISTS",
            message="Já existe um cliente cadastrado com este CNPJ.",
        )
