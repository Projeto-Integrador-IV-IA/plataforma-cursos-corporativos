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

    @field_validator("original_content")
    @classmethod
    def reject_blank_content(cls, value: str) -> str:
        if not value.strip():
            raise ValueError("original_content must not be blank")
        return value


class RawInputRead(BaseModel):
    """Fonte confirmada pelo banco antes de qualquer processamento posterior."""

    model_config = ConfigDict(from_attributes=True)

    id: UUID
    demand_id: UUID
    original_content: str
    source: RawInputSource
    author_id: UUID
    created_at: datetime


class RawInputErrorDetails(BaseModel):
    code: str
    message: str
    details: dict[str, str] = Field(default_factory=dict)
    request_id: str | None = None


class RawInputErrorResponse(BaseModel):
    error: RawInputErrorDetails
