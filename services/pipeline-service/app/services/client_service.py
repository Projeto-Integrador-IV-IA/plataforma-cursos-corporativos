"""Caso de uso: gestao de clientes (RF01, RF03).

Regras: nome corporativo obrigatorio e unico por CNPJ quando informado;
cliente com demandas ativas nao pode ser removido.

Implementa somente o caso de uso de cadastro nesta entrega.
"""

from app.models.client import Client
from app.repositories.client_repository import ClientRepository
from app.schemas.client import ClientCreate


class ClientCnpjConflictError(Exception):
    pass


class ClientService:
    def __init__(self, repository: ClientRepository) -> None:
        self.repository = repository

    def create(self, data: ClientCreate) -> Client:
        if data.cnpj and self.repository.get_by_cnpj(data.cnpj):
            raise ClientCnpjConflictError("Ja existe um cliente cadastrado com este CNPJ.")
        return self.repository.create(data)
