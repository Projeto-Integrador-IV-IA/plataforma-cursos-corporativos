"""Contratos para persistir e consultar resultados da IA (RF16.1 consolidado)."""

from datetime import datetime
from typing import Any
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, field_validator

from app.domain.enums import ArtifactOrigin, ArtifactType, RawInputSource


class ArtifactResultCreate(BaseModel):
    """Resultado bruto e estruturado, mais todas as fontes que o produziram."""

    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)

    type: ArtifactType = ArtifactType.REQUISITOS_EXTRAIDOS
    title: str | None = None
    raw_output: str = Field(min_length=1, description="Resposta integral devolvida pelo LLM.")
    structured_content: dict[str, Any] = Field(
        description="Resultado ja validado contra o schema canonico."
    )
    raw_input_ids: list[UUID] = Field(
        min_length=1,
        description="Fontes da mesma demanda utilizadas na geracao.",
    )
    ai_metadata: dict[str, Any] | None = Field(
        default=None,
        description="Modelo, prompt, tokens e latencia da execucao.",
    )

    @field_validator("raw_input_ids")
    @classmethod
    def sources_must_be_unique(cls, value: list[UUID]) -> list[UUID]:
        if len(value) != len(set(value)):
            raise ValueError("raw_input_ids must not contain duplicates")
        return value


class ArtifactSourceRead(BaseModel):
    """Referencia suficiente para recuperar e auditar uma fonte usada."""

    model_config = ConfigDict(from_attributes=True)

    id: UUID
    source: RawInputSource
    created_at: datetime


class ArtifactVersionRead(BaseModel):
    """Primeira versao atomica do resultado da IA."""

    model_config = ConfigDict(from_attributes=True)

    id: UUID
    number: int
    raw_output: str = Field(validation_alias="raw_content")
    structured_content: dict[str, Any] = Field(validation_alias="content")
    origin: ArtifactOrigin
    ai_metadata: dict[str, Any] | None
    created_at: datetime


class ArtifactRead(BaseModel):
    """Artefato recuperavel pela demanda, com fontes e versoes."""

    id: UUID
    demand_id: UUID
    type: ArtifactType
    title: str | None
    created_at: datetime
    sources: list[ArtifactSourceRead]
    versions: list[ArtifactVersionRead]


class ArtifactErrorDetails(BaseModel):
    code: str
    message: str
    details: dict[str, str] = Field(default_factory=dict)
    request_id: str | None = None


class ArtifactErrorResponse(BaseModel):
    error: ArtifactErrorDetails
