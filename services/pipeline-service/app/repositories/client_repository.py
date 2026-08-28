"""Persistencia de clientes (RF01, RF03).

Operacoes previstas: criar, obter por id, atualizar, listar com filtro por
nome/segmento e paginacao.

Implementa somente as operacoes necessarias ao cadastro nesta entrega.
"""

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.client import Client
from app.schemas.client import ClientCreate


class ClientRepository:
    def __init__(self, session: Session) -> None:
        self.session = session

    def get_by_cnpj(self, cnpj: str) -> Client | None:
        return self.session.scalar(select(Client).where(Client.cnpj == cnpj))

    def create(self, data: ClientCreate) -> Client:
        client = Client(**data.model_dump())
        self.session.add(client)
        self.session.flush()
        self.session.refresh(client)
        return client
