"""Contratos publicos da API de clientes (RF01.1 e RF01.2)."""

import re
from datetime import datetime
from typing import Annotated
from uuid import UUID

from pydantic import BaseModel, ConfigDict, EmailStr, Field, field_validator

CNPJ_PATTERN = re.compile(r"^(?:[0-9]{14}|[0-9]{2}\.[0-9]{3}\.[0-9]{3}/[0-9]{4}-[0-9]{2})$")
PHONE_PATTERN = re.compile(r"^\+?[0-9() -]+$")

ClientName = Annotated[str, Field(min_length=1, max_length=200)]
Cnpj = Annotated[
    str,
    Field(max_length=18, json_schema_extra={"pattern": CNPJ_PATTERN.pattern}),
]
Segment = Annotated[str, Field(min_length=1, max_length=120)]
ContactName = Annotated[str, Field(min_length=1, max_length=200)]
ContactEmail = Annotated[EmailStr, Field(max_length=200)]
ContactPhone = Annotated[
    str,
    Field(min_length=10, max_length=40, json_schema_extra={"pattern": PHONE_PATTERN.pattern}),
]


def normalize_cnpj(value: Cnpj | None) -> str | None:
    """Aceita CNPJ com ou sem mascara e persiste somente os 14 digitos."""

    if value is None:
        return None
    if CNPJ_PATTERN.fullmatch(value) is None:
        raise ValueError("CNPJ deve conter 14 digitos, com ou sem mascara")
    return value.translate(str.maketrans("", "", "./-"))


def validate_contact_phone(value: ContactPhone | None) -> str | None:
    """Aceita telefone nacional ou internacional com formatacao usual."""

    if value is None:
        return None
    if PHONE_PATTERN.fullmatch(value) is None:
        raise ValueError(
            "telefone deve usar somente numeros, espacos, parenteses, hifen e prefixo +"
        )
    digit_count = sum(character.isdigit() for character in value)
    if not 10 <= digit_count <= 15:
        raise ValueError("telefone deve conter entre 10 e 15 digitos")
    return value


class ClientCreate(BaseModel):
    """Dados cadastrais recebidos pelo fluxo dependente RF01.1."""

    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)

    name: ClientName
    cnpj: Cnpj | None = None
    segment: Segment | None = None
    contact_name: ContactName | None = None
    contact_email: ContactEmail | None = None
    contact_phone: ContactPhone | None = None
    notes: str | None = None

    _normalize_cnpj = field_validator("cnpj")(normalize_cnpj)
    _validate_contact_phone = field_validator("contact_phone")(validate_contact_phone)


class ClientUpdate(BaseModel):
    """Edicao parcial; campos omitidos permanecem inalterados (RF01.2)."""

    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)

    name: ClientName | None = None
    cnpj: Cnpj | None = None
    segment: Segment | None = None
    contact_name: ContactName | None = None
    contact_email: ContactEmail | None = None
    contact_phone: ContactPhone | None = None
    notes: str | None = None

    @field_validator("name")
    @classmethod
    def reject_null_name(cls, value: str | None) -> str:
        if value is None:
            raise ValueError("name cannot be null")
        return value

    _normalize_cnpj = field_validator("cnpj")(normalize_cnpj)
    _validate_contact_phone = field_validator("contact_phone")(validate_contact_phone)


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
