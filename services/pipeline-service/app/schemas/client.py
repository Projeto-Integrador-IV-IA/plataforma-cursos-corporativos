"""DTOs de entrada e saida (Pydantic).

Separados dos modelos ORM de proposito: o que a API expoe e contrato publico
(RNF02) e nao deve mudar so porque o schema do banco mudou.

Convencao de nomes: XxxCreate (entrada de criacao), XxxUpdate (edicao parcial),
XxxRead (saida), XxxDetail (saida com relacionamentos).

Implementa os contratos necessarios para o cadastro de cliente.
"""

import uuid
from datetime import datetime

from pydantic import BaseModel, ConfigDict, EmailStr, Field, field_validator


class ClientCreate(BaseModel):
    nome: str = Field(min_length=1)
    cnpj: str | None = None
    segmento: str | None = None
    contato_nome: str | None = None
    contato_email: EmailStr | None = None
    contato_telefone: str | None = None
    observacoes: str | None = None

    @field_validator("nome")
    @classmethod
    def nome_nao_pode_ser_vazio(cls, value: str) -> str:
        value = value.strip()
        if not value:
            raise ValueError("nome nao pode ser vazio")
        return value

    @field_validator("cnpj")
    @classmethod
    def normalizar_cnpj(cls, value: str | None) -> str | None:
        if value is None:
            return None
        digits = "".join(character for character in value if character.isdigit())
        if len(digits) != 14:
            raise ValueError("cnpj deve conter 14 digitos")
        return digits


class ClientRead(BaseModel):
    id: uuid.UUID
    nome: str
    cnpj: str | None
    segmento: str | None
    contato_nome: str | None
    contato_email: str | None
    contato_telefone: str | None
    observacoes: str | None
    ativo: bool
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)
