"""Contratos publicos da API de clientes (RF01.1 e RF01.2)."""

import re
from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, field_validator

CNPJ_PATTERN = re.compile(r"(?:[0-9]{14}|[0-9]{2}\.[0-9]{3}\.[0-9]{3}/[0-9]{4}-[0-9]{2})")


def normalize_cnpj(value: str | None) -> str | None:
    """Aceita CNPJ com ou sem mascara e persiste somente os 14 digitos."""

    if value is None:
        return None
    if CNPJ_PATTERN.fullmatch(value) is None:
        raise ValueError("cnpj must contain 14 digits, formatted or unformatted")
    return value.translate(str.maketrans("", "", "./-"))


class ClientCreate(BaseModel):
    """Dados cadastrais recebidos pelo fluxo dependente RF01.1."""

    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)

    name: str = Field(min_length=1)
    cnpj: str | None = None
    segment: str | None = None
    contact_name: str | None = None
    contact_email: str | None = None
    contact_phone: str | None = None
    notes: str | None = None

    _normalize_cnpj = field_validator("cnpj")(normalize_cnpj)


class ClientUpdate(BaseModel):
    """Edicao parcial; campos omitidos permanecem inalterados (RF01.2)."""

    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)

    name: str | None = Field(default=None, min_length=1)
    cnpj: str | None = None
    segment: str | None = None
    contact_name: str | None = None
    contact_email: str | None = None
    contact_phone: str | None = None
    notes: str | None = None

    @field_validator("name")
    @classmethod
    def reject_null_name(cls, value: str | None) -> str:
        if value is None:
            raise ValueError("name cannot be null")
        return value

    _normalize_cnpj = field_validator("cnpj")(normalize_cnpj)


class ClientRead(BaseModel):
    """Representacao completa usada na listagem e na tela de detalhe."""

    model_config = ConfigDict(from_attributes=True)

    id: UUID
    name: str
    cnpj: str | None
    segment: str | None
    contact_name: str | None
    contact_email: str | None
    contact_phone: str | None
    notes: str | None
    active: bool
    created_at: datetime
    updated_at: datetime


class ClientPage(BaseModel):
    """Pagina estavel para a consulta de clientes."""

    items: list[ClientRead]
    total: int
    page: int
    size: int
