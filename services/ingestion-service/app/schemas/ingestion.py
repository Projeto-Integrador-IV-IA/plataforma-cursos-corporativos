"""Contrato publico da captacao padronizada de texto bruto (RF09)."""

from datetime import datetime
from typing import Any, Literal
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, field_validator

from app.domain.raw_demand import PersistedRawDemand, RawDemand, SourceKind
from app.normalizers.source_detector import detect_source_type


class IngestionCreate(BaseModel):
    """Texto, origem opcional e demanda de destino; a declaracao prevalece sobre a inferencia."""

    model_config = ConfigDict(extra="forbid")

    text: str = Field(min_length=1, description="Texto bruto preservado sem alteracoes.")
    source_type: SourceKind | None = Field(
        default=None,
        description=(
            "Canal declarado pelo operador; ausente ou nulo permite inferencia "
            "pelo formato do texto."
        ),
    )
    demand_id: UUID = Field(description="Demanda existente no pipeline-service.")

    @field_validator("text")
    @classmethod
    def reject_blank_text(cls, value: str) -> str:
        if not value.strip():
            raise ValueError("text must not be blank")
        return value

    def to_domain(self) -> RawDemand:
        return RawDemand(
            demand_id=self.demand_id,
            text=self.text,
            source_type=self.source_type
            if self.source_type is not None
            else detect_source_type(self.text),
        )


class IngestionRead(BaseModel):
    """Resposta emitida somente depois da confirmacao do pipeline-service."""

    raw_input_id: UUID
    demand_id: UUID
    source_type: SourceKind
    status: Literal["RECEBIDA"] = "RECEBIDA"
    created_at: datetime

    @classmethod
    def from_domain(cls, persisted: PersistedRawDemand) -> "IngestionRead":
        return cls(
            raw_input_id=persisted.raw_input_id,
            demand_id=persisted.demand_id,
            source_type=persisted.source_type,
            created_at=persisted.created_at,
        )


class ErrorBody(BaseModel):
    code: str
    message: str
    details: dict[str, Any] | None = None
    request_id: str | None = None


class ErrorResponse(BaseModel):
    error: ErrorBody
