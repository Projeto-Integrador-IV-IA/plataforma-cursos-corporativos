"""Persistencia de clientes (RF01, RF03).

Operacoes previstas: criar, obter por id, atualizar e listar com paginacao.

Implementa as operacoes necessarias a RF01.1.
"""

import uuid

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.models.client import Client
from app.schemas.client import ClientCreate


class ClientRepository:
    def __init__(self, session: Session) -> None:
        self.session = session

    def get_by_cnpj(self, cnpj: str) -> Client | None:
        return self.session.scalar(select(Client).where(Client.cnpj == cnpj))

    def get_by_id(self, client_id: uuid.UUID) -> Client | None:
        return self.session.get(Client, client_id)

    def list(self, *, page: int, size: int) -> tuple[list[Client], int]:
        total = self.session.scalar(select(func.count()).select_from(Client)) or 0
        statement = (
            select(Client)
            .order_by(Client.created_at.desc(), Client.id)
            .offset((page - 1) * size)
            .limit(size)
        )
        return list(self.session.scalars(statement)), total

    def create(self, data: ClientCreate) -> Client:
        client = Client(**data.model_dump())
        self.session.add(client)
        self.session.flush()
        self.session.commit()
        self.session.refresh(client)
        return client

    def rollback(self) -> None:
        self.session.rollback()
