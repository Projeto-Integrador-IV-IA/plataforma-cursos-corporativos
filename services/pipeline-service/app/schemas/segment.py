"""Contratos para persistir e consultar trechos citaveis das fontes."""

from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator


class SourceSegmentCreate(BaseModel):
    """Trecho identificado de forma estavel pelo ingestion-service."""

    model_config = ConfigDict(extra="forbid")

    id: UUID
    position: int = Field(ge=1)
    content: str = Field(min_length=1)
    original_start_offset: int = Field(
        ge=0,
        description="Indice de caractere inicial, inclusivo, no conteudo original da fonte.",
    )
    original_end_offset: int = Field(
        ge=1,
        description="Indice de caractere final, exclusivo, no conteudo original da fonte.",
    )

    @model_validator(mode="after")
    def validate_original_span(self) -> "SourceSegmentCreate":
        if self.original_end_offset <= self.original_start_offset:
            raise ValueError("original_end_offset must be after original_start_offset")
        return self

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
    original_start_offset: int | None = Field(
        description="Indice inicial na fonte original; nulo em registros legados sem mapeamento."
    )
    original_end_offset: int | None = Field(
        description=(
            "Indice final exclusivo na fonte original; nulo em registros legados sem mapeamento."
        )
    )
    original_content: str | None = Field(
        description=(
            "Fatia literal da fonte original indicada pelos offsets; nula sem mapeamento legado."
        )
    )


class SourceSegmentErrorDetails(BaseModel):
    code: str
    message: str
    details: dict[str, str] = Field(default_factory=dict)
    request_id: str | None = None


class SourceSegmentErrorResponse(BaseModel):
    error: SourceSegmentErrorDetails
