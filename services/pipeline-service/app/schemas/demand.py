"""Contrato de criacao de demandas vinculadas a clientes (RF02)."""

from datetime import datetime
from typing import Any
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, field_validator

from app.domain.enums import DemandStatus, PipelineStage, RawInputSource


class DemandCreate(BaseModel):
    """Dados da negociacao; situacao e etapa inicial sao definidas pelo servico."""

    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)

    client_id: UUID = Field(description="Identificador de um cliente existente. Obrigatorio.")
    title: str = Field(min_length=1, description="Titulo da negociacao.")
    description: str | None = Field(default=None, description="Contexto da negociacao.")
    owner_id: UUID | None = Field(default=None, description="Identificador do usuario responsavel.")


class DemandUpdate(BaseModel):
    """Campos de contexto editaveis sem substituir os demais dados da demanda."""

    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)

    title: str | None = Field(default=None, min_length=1, description="Titulo da negociacao.")
    description: str | None = Field(default=None, description="Contexto da negociacao.")
    owner_id: UUID | None = Field(default=None, description="Identificador do usuario responsavel.")

    @field_validator("title")
    @classmethod
    def title_cannot_be_null(cls, value: str | None) -> str | None:
        if value is None:
            raise ValueError("O titulo nao pode ser nulo.")
        return value


class DemandRead(BaseModel):
    """Demanda persistida, com situacao, etapa corrente e vinculo ao cliente."""

    model_config = ConfigDict(from_attributes=True)

    id: UUID
    client_id: UUID
    title: str
    description: str | None
    owner_id: UUID | None
    status: DemandStatus
    current_stage: PipelineStage
    active: bool
    created_at: datetime
    updated_at: datetime


class DemandClientRead(BaseModel):
    """Cliente incorporado ao detalhe para evitar uma segunda consulta da tela."""

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


class DemandArtifactVersionRead(BaseModel):
    """Versao de artefato disponibilizada para a estrutura gerada no detalhe."""

    model_config = ConfigDict(from_attributes=True)

    id: UUID
    number: int
    content: dict[str, Any]
    origin: str
    ai_metadata: dict[str, Any] | None
    author_id: UUID | None
    created_at: datetime


class DemandArtifactRead(BaseModel):
    """Artefato vinculado com suas versoes em ordem crescente."""

    model_config = ConfigDict(from_attributes=True)

    id: UUID
    type: str
    title: str | None
    raw_input_id: UUID | None
    created_at: datetime
    versions: list[DemandArtifactVersionRead]


class DemandRawInputRead(BaseModel):
    """Fonte bruta captada, devolvida no detalhe para provar que nada se perdeu.

    O conteudo original entra por inteiro: preserva-lo e o proprio requisito
    (RF09, RNF05), e a tela nao teria como confirmar a integridade a partir de
    um resumo. ``normalized_content`` fica de fora enquanto a sanitizacao
    (RF11) nao tiver contrato publicado.
    """

    model_config = ConfigDict(from_attributes=True)

    id: UUID
    source: RawInputSource
    original_content: str
    truncated: bool
    author_id: UUID
    created_at: datetime


class DemandDetail(DemandRead):
    """Agregado usado pela tela de detalhe da demanda."""

    client: DemandClientRead
    raw_inputs: list[DemandRawInputRead]
    artifacts: list[DemandArtifactRead]
