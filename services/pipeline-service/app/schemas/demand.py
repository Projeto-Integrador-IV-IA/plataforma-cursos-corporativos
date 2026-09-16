"""Contrato de criacao de demandas vinculadas a clientes (RF02)."""

from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field

from app.domain.enums import DemandStatus, PipelineStage


class DemandCreate(BaseModel):
    """Dados da negociacao; situacao e etapa inicial sao definidas pelo servico."""

    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)

    client_id: UUID = Field(description="Identificador de um cliente existente. Obrigatorio.")
    title: str = Field(min_length=1, description="Titulo da negociacao.")
    description: str | None = Field(default=None, description="Contexto da negociacao.")
    owner_id: UUID | None = Field(default=None, description="Identificador do usuario responsavel.")


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


class DemandErrorDetails(BaseModel):
    """Erro previsivel, sem detalhes internos do banco."""

    code: str
    message: str
    details: dict[str, str] = Field(default_factory=dict)
    request_id: str | None = None


class DemandErrorResponse(BaseModel):
    """Envelope de erro acordado para a plataforma (RNF02)."""

    error: DemandErrorDetails
