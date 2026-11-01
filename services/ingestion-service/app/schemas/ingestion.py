"""Contrato publico da captacao padronizada de texto bruto (RF09)."""

from datetime import datetime
from typing import Any, Final, Literal
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, field_validator
from pydantic_core import PydanticCustomError

from app.domain.raw_demand import PersistedRawDemand, RawDemand, SourceKind
from app.normalizers.source_detector import detect_source_type

SOURCE_TEXT_MIN_CONTENT_LENGTH: Final[int] = 10
SOURCE_TEXT_MAX_LENGTH: Final[int] = 50_000


class IngestionCreate(BaseModel):
    """Texto, origem opcional e demanda de destino; a declaracao prevalece sobre a inferencia."""

    model_config = ConfigDict(extra="forbid")

    text: str = Field(
        min_length=SOURCE_TEXT_MIN_CONTENT_LENGTH,
        max_length=SOURCE_TEXT_MAX_LENGTH,
        description=(
            "Texto bruto preservado sem alteracoes. Deve conter pelo menos 10 caracteres "
            "nao brancos e no maximo 50.000 caracteres no total."
        ),
    )
    source_type: SourceKind | None = Field(
        default=None,
        description=(
            "Canal declarado pelo operador; ausente ou nulo permite inferencia "
            "pelo formato do texto."
        ),
    )
    demand_id: UUID = Field(description="Demanda existente no pipeline-service.")
    previous_attempt_id: UUID | None = Field(
        default=None,
        description="Tentativa anterior da mesma demanda, quando esta captacao for reprocessamento.",
    )

    @field_validator("text", mode="before")
    @classmethod
    def validate_source_text(cls, value: object) -> object:
        if not isinstance(value, str):
            raise PydanticCustomError(
                "source_text_invalid_format",
                "O conteudo da fonte deve ser enviado como texto.",
            )

        content_length = sum(not character.isspace() for character in value)
        if content_length < SOURCE_TEXT_MIN_CONTENT_LENGTH:
            raise PydanticCustomError(
                "source_text_too_short",
                "A fonte deve conter pelo menos {minimum} caracteres nao brancos.",
                {"minimum": SOURCE_TEXT_MIN_CONTENT_LENGTH},
            )
        if len(value) > SOURCE_TEXT_MAX_LENGTH:
            raise PydanticCustomError(
                "source_text_too_long",
                "A fonte deve conter no maximo {maximum} caracteres.",
                {"maximum": SOURCE_TEXT_MAX_LENGTH},
            )
        return value

    @field_validator("source_type", mode="before")
    @classmethod
    def validate_source_type(cls, value: object) -> object:
        if value is None or isinstance(value, SourceKind):
            return value
        if isinstance(value, str) and value in {source.value for source in SourceKind}:
            return value

        accepted = ", ".join(source.value for source in SourceKind)
        raise PydanticCustomError(
            "source_type_invalid",
            "O formato da fonte e invalido. Use um de: {accepted}.",
            {"accepted": accepted},
        )

    def to_domain(self) -> RawDemand:
        return RawDemand(
            demand_id=self.demand_id,
            text=self.text,
            source_type=self.source_type
            if self.source_type is not None
            else detect_source_type(self.text),
            previous_attempt_id=self.previous_attempt_id,
        )


class IngestionRead(BaseModel):
    """Resposta emitida somente depois da confirmacao do pipeline-service."""

    raw_input_id: UUID
    demand_id: UUID
    source_type: SourceKind
    previous_attempt_id: UUID | None
    status: Literal["RECEBIDA"] = "RECEBIDA"
    created_at: datetime

    @classmethod
    def from_domain(cls, persisted: PersistedRawDemand) -> "IngestionRead":
        return cls(
            raw_input_id=persisted.raw_input_id,
            demand_id=persisted.demand_id,
            source_type=persisted.source_type,
            previous_attempt_id=persisted.previous_attempt_id,
            created_at=persisted.created_at,
        )


class ErrorBody(BaseModel):
    code: str
    message: str
    details: dict[str, Any] | None = None
    request_id: str | None = None


class ErrorResponse(BaseModel):
    error: ErrorBody
