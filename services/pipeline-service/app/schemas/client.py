"""DTOs de entrada e saida (Pydantic).

Separados dos modelos ORM de proposito: o que a API expoe e contrato publico
(RNF02) e nao deve mudar so porque o schema do banco mudou.

Convencao de nomes: XxxCreate (entrada de criacao), XxxUpdate (edicao parcial),
XxxRead (saida), XxxDetail (saida com relacionamentos).

Implementa os contratos necessarios para cadastro e consulta de clientes.
"""

import re
import uuid
from datetime import datetime

from pydantic import BaseModel, ConfigDict, EmailStr, Field, field_validator

CNPJ_PATTERN = re.compile(r"(?:[0-9]{14}|[0-9]{2}\.[0-9]{3}\.[0-9]{3}/[0-9]{4}-[0-9]{2})")


class ClientCreate(BaseModel):
    name: str = Field(min_length=1)
    cnpj: str | None = None
    segment: str | None = None
    contact_name: str | None = None
    contact_email: EmailStr | None = None
    contact_phone: str | None = None
    notes: str | None = None

    @field_validator("name")
    @classmethod
    def validate_name(cls, value: str) -> str:
        value = value.strip()
        if not value:
            raise ValueError("name must not be blank")
        return value

    @field_validator("cnpj")
    @classmethod
    def normalize_cnpj(cls, value: str | None) -> str | None:
        if value is None:
            return None
        if CNPJ_PATTERN.fullmatch(value) is None:
            raise ValueError("cnpj must contain 14 digits, formatted or unformatted")
        return value.translate(str.maketrans("", "", "./-"))


class ClientRead(BaseModel):
    id: uuid.UUID
    name: str
    cnpj: str | None
    segment: str | None
    contact_name: str | None
    contact_email: EmailStr | None
    contact_phone: str | None
    notes: str | None
    active: bool
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


class ClientPage(BaseModel):
    items: list[ClientRead]
    total: int
    page: int
    size: int
