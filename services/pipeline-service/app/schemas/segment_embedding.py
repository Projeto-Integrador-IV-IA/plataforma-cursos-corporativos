"""Contratos de gravacao em lote e busca por similaridade de embeddings (RNF28 consolidado)."""

from datetime import datetime
from typing import Self
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, field_validator

from app.models._types import EMBEDDING_DIMENSION
from app.models.raw_input import SourceSegment
from app.models.segment_embedding import SegmentEmbedding


class SegmentEmbeddingCreate(BaseModel):
    """Um embedding, de um modelo, para um trecho ja persistido."""

    model_config = ConfigDict(extra="forbid")

    segment_id: UUID
    model: str = Field(min_length=1, description="Identificador do modelo que gerou o vetor.")
    vector: list[float] = Field(
        min_length=EMBEDDING_DIMENSION,
        max_length=EMBEDDING_DIMENSION,
        description=f"Vetor de dimensao fixa ({EMBEDDING_DIMENSION}).",
    )


class SegmentEmbeddingBatchCreate(BaseModel):
    """Lote de embeddings - os trechos de uma fonte sao gerados juntos."""

    model_config = ConfigDict(extra="forbid")

    embeddings: list[SegmentEmbeddingCreate] = Field(min_length=1)

    @field_validator("embeddings")
    @classmethod
    def no_duplicate_segment_and_model(
        cls, value: list[SegmentEmbeddingCreate]
    ) -> list[SegmentEmbeddingCreate]:
        pares = [(item.segment_id, item.model) for item in value]
        if len(pares) != len(set(pares)):
            raise ValueError("embeddings must not repeat the same (segment_id, model) pair")
        return value


class SegmentEmbeddingRead(BaseModel):
    """Confirmacao de gravacao - sem o vetor de volta, que o chamador ja tem."""

    model_config = ConfigDict(from_attributes=True)

    segment_id: UUID
    model: str
    created_at: datetime

    @classmethod
    def from_model(cls, embedding: SegmentEmbedding) -> Self:
        return cls.model_validate(embedding)


class SimilaritySearchRequest(BaseModel):
    """Consulta: um vetor de um modelo, com quantos e quao parecidos trechos voltam."""

    model_config = ConfigDict(extra="forbid")

    model: str = Field(min_length=1, description="Mesmo modelo usado para gerar os embeddings.")
    vector: list[float] = Field(min_length=EMBEDDING_DIMENSION, max_length=EMBEDDING_DIMENSION)
    top_k: int = Field(default=5, ge=1, le=50, description="Teto de trechos devolvidos.")
    min_similarity: float = Field(
        default=0.0,
        ge=-1.0,
        le=1.0,
        description="Piso de similaridade de cosseno; trecho abaixo nao entra no resultado.",
    )


class SimilaritySearchResult(BaseModel):
    """Um trecho encontrado, com a similaridade que o trouxe ao resultado."""

    model_config = ConfigDict(frozen=True)

    segment_id: UUID
    raw_input_id: UUID
    position: int
    content: str
    similarity: float

    @classmethod
    def from_match(cls, segment: SourceSegment, similarity: float) -> Self:
        return cls(
            segment_id=segment.id,
            raw_input_id=segment.raw_input_id,
            position=segment.position,
            content=segment.content,
            similarity=similarity,
        )


class SimilaritySearchResponse(BaseModel):
    """Trechos mais proximos, ordenados do mais para o menos similar."""

    model_config = ConfigDict(frozen=True)

    results: list[SimilaritySearchResult]


class SegmentEmbeddingErrorDetails(BaseModel):
    code: str
    message: str
    details: dict[str, str] = Field(default_factory=dict)
    request_id: str | None = None


class SegmentEmbeddingErrorResponse(BaseModel):
    error: SegmentEmbeddingErrorDetails
