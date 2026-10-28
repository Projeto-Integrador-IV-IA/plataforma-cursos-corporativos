"""Persistencia de clientes (RF01.1, RF01.2 e RF01.3)."""

from collections.abc import Mapping
from datetime import UTC, datetime
from typing import Any
from uuid import UUID

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.models.client import Client
from app.schemas.client import ClientCreate


class ClientRepository:
    """Isola consultas e escritas sem encerrar a transacao da requisicao."""

    def __init__(self, session: Session) -> None:
        self.session = session

    def get_by_cnpj(self, cnpj: str) -> Client | None:
        return self.session.scalar(select(Client).where(Client.cnpj == cnpj))

    def get_by_id(self, client_id: UUID) -> Client | None:
        return self.session.get(Client, client_id)

    def list(
        self, *, page: int, size: int, include_inactive: bool = False
    ) -> tuple[list[Client], int]:
        count_statement = select(func.count()).select_from(Client)
        statement = select(Client)
        if not include_inactive:
            count_statement = count_statement.where(Client.active.is_(True))
            statement = statement.where(Client.active.is_(True))

        total = self.session.scalar(count_statement) or 0
        statement = (
            statement.order_by(Client.created_at.desc(), Client.id)
            .offset((page - 1) * size)
            .limit(size)
        )
        return list(self.session.scalars(statement)), total

    def create(self, data: ClientCreate) -> Client:
        client = Client(**data.model_dump())
        self.session.add(client)
        self.session.flush()
        self.session.refresh(client)
        return client

    def update(self, client: Client, changes: Mapping[str, Any]) -> Client:
        for field, value in changes.items():
            setattr(client, field, value)
        client.updated_at = datetime.now(UTC)
        self.session.flush()
        self.session.refresh(client)
        return client

    def set_active(self, client: Client, active: bool) -> Client:
        if client.active is active:
            return client
        client.active = active
        client.updated_at = datetime.now(UTC)
        self.session.flush()
        self.session.refresh(client)
        return client

    def rollback(self) -> None:
        self.session.rollback()
