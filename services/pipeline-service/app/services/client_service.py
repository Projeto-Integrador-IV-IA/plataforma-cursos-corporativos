"""Casos de uso de cadastro, consulta e edicao de clientes (RF01)."""

from uuid import UUID

from sqlalchemy.exc import IntegrityError

from app.core.exceptions import ConflictError, NotFoundError
from app.models.client import Client
from app.repositories.client_repository import ClientRepository
from app.schemas.client import ClientCreate, ClientPage, ClientRead, ClientUpdate


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

    def get(self, client_id: UUID) -> Client:
        client = self.repository.get_by_id(client_id)
        if client is None:
            raise NotFoundError(
                code="CLIENT_NOT_FOUND",
                message="Cliente nao encontrado.",
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

    def update(self, client_id: UUID, data: ClientUpdate) -> Client:
        client = self.get(client_id)
        changes = data.model_dump(exclude_unset=True)
        if not changes:
            return client

        if "cnpj" in changes and changes["cnpj"] is not None:
            duplicate = self.repository.get_by_cnpj(changes["cnpj"])
            if duplicate is not None and duplicate.id != client.id:
                raise self._cnpj_conflict()

        try:
            return self.repository.update(client, changes)
        except IntegrityError as exc:
            self.repository.rollback()
            raise self._cnpj_conflict() from exc

    @staticmethod
    def _cnpj_conflict() -> ConflictError:
        return ConflictError(
            code="CLIENT_CNPJ_ALREADY_EXISTS",
            message="Ja existe um cliente cadastrado com este CNPJ.",
        )
