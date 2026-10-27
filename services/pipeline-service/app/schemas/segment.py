"""Contratos para persistir e consultar trechos citaveis das fontes."""

from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, field_validator


class SourceSegmentCreate(BaseModel):
    """Trecho identificado de forma estavel pelo ingestion-service."""

    model_config = ConfigDict(extra="forbid")

    id: UUID
    position: int = Field(ge=1)
    content: str = Field(min_length=1)

    @field_validator("content")
    @classmethod
    def reject_blank_content(cls, value: str) -> str:
        if not value.strip():
            raise ValueError("content must not be blank")
        return value


class SourceSegmentBatchCreate(BaseModel):
    """Lote atomico dos trechos gerados para uma unica fonte."""

    model_config = ConfigDict(extra="forbid")

    segments: list[SourceSegmentCreate] = Field(min_length=1)

    @field_validator("segments")
    @classmethod
    def reject_duplicate_ids_or_positions(
        cls, value: list[SourceSegmentCreate]
    ) -> list[SourceSegmentCreate]:
        ids = [segment.id for segment in value]
        positions = [segment.position for segment in value]
        if len(ids) != len(set(ids)):
            raise ValueError("segment ids must not contain duplicates")
        if len(positions) != len(set(positions)):
            raise ValueError("segment positions must not contain duplicates")
        return value


class SourceSegmentRead(BaseModel):
    """Trecho recuperavel com os vinculos de fonte e demanda."""

    model_config = ConfigDict(from_attributes=True)

    id: UUID
    raw_input_id: UUID
    demand_id: UUID
    position: int
    content: str


class SourceSegmentErrorDetails(BaseModel):
    code: str
    message: str
    details: dict[str, str] = Field(default_factory=dict)
    request_id: str | None = None


class SourceSegmentErrorResponse(BaseModel):
    error: SourceSegmentErrorDetails
