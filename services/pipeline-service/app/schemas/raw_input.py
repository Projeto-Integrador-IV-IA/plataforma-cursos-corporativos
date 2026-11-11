"""Contrato interno para persistir uma fonte bruta vinculada a uma demanda."""

from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, field_validator

from app.domain.enums import RawInputSource


class RawInputCreate(BaseModel):
    """Conteudo original recebido do ingestion-service."""

    model_config = ConfigDict(extra="forbid")

    original_content: str = Field(min_length=1)
    source: RawInputSource
    previous_attempt_id: UUID | None = None

    @field_validator("source")
    @classmethod
    def reject_audio_without_file(cls, value: RawInputSource) -> RawInputSource:
        if value == RawInputSource.AUDIO:
            raise ValueError("Para audio, use a rota de upload de arquivo.")
        return value

    @field_validator("original_content")
    @classmethod
    def reject_blank_content(cls, value: str) -> str:
        if not value.strip():
            raise ValueError("original_content must not be blank")
        return value


class AudioMetadata(BaseModel):
    """Metadados consultaveis sem carregar o binario nas listagens."""

    model_config = ConfigDict(from_attributes=True)

    filename: str = Field(min_length=1, max_length=255)
    content_type: str = Field(min_length=1, max_length=64)
    size_bytes: int = Field(gt=0)
    duration_seconds: float = Field(gt=0, allow_inf_nan=False)
    sha256: str = Field(pattern="^[a-f0-9]{64}$")


class RawInputRead(BaseModel):
    """Fonte confirmada pelo banco antes de qualquer processamento posterior."""

    model_config = ConfigDict(from_attributes=True)

    id: UUID
    demand_id: UUID
    received_order: int = Field(ge=1)
    original_content: str
    normalized_content: str | None
    previous_attempt_id: UUID | None
    source: RawInputSource
    author_id: UUID
    truncated: bool
    created_at: datetime
    audio: AudioMetadata | None = None


class RawInputNormalization(BaseModel):
    """Copia sanitizada; o contrato nao aceita o conteudo original nesta operacao."""

    model_config = ConfigDict(extra="forbid")

    normalized_content: str


class RawInputErrorDetails(BaseModel):
    code: str
    message: str
    details: dict[str, str] = Field(default_factory=dict)
    request_id: str | None = None


class RawInputErrorResponse(BaseModel):
    error: RawInputErrorDetails
