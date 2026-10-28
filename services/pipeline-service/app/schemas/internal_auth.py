"""Contrato interno de credenciais entre pipeline e gateway (RF26)."""

from uuid import UUID

from pydantic import BaseModel, ConfigDict, EmailStr


class InternalUserCredentials(BaseModel):
    """Inclui o hash somente na rota interna autenticada por chave de servico."""

    model_config = ConfigDict(from_attributes=True)

    id: UUID
    name: str
    email: EmailStr
    password_hash: str
    role: str
    active: bool
