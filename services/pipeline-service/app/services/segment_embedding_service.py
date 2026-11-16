"""Caso de uso de gravacao em lote e busca por similaridade de embeddings (RNF28 consolidado)."""

import sqlite3
from uuid import UUID

from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.core.exceptions import ConflictError, NotFoundError
from app.models import Demand
from app.models.segment_embedding import SegmentEmbedding
from app.repositories.segment_embedding_repository import SegmentEmbeddingRepository
from app.schemas.segment_embedding import (
    SegmentEmbeddingBatchCreate,
    SegmentEmbeddingRead,
    SimilaritySearchRequest,
    SimilaritySearchResponse,
    SimilaritySearchResult,
)


class SegmentEmbeddingService:
    def __init__(self, session: Session) -> None:
        self.session = session
        self.repository = SegmentEmbeddingRepository(session)

    def save_batch(self, data: SegmentEmbeddingBatchCreate) -> list[SegmentEmbeddingRead]:
        segment_ids = [item.segment_id for item in data.embeddings]
        found = self.repository.get_segments(segment_ids)
        found_by_id = {segment.id: segment for segment in found}
        missing = [segment_id for segment_id in segment_ids if segment_id not in found_by_id]
        if missing:
            raise NotFoundError(
                code="SOURCE_SEGMENT_NOT_FOUND",
                message="Um ou mais trechos nao foram encontrados.",
                details={"segment_ids": ",".join(map(str, missing))},
            )

        embeddings = [
            SegmentEmbedding(segment_id=item.segment_id, model=item.model, vector=item.vector)
            for item in data.embeddings
        ]
        try:
            created = self.repository.insert_batch(embeddings)
        except IntegrityError as exc:
            self.session.rollback()
            is_unique_violation = (
                getattr(exc.orig, "sqlstate", None) == "23505"
                or getattr(exc.orig, "sqlite_errorcode", None)
                == sqlite3.SQLITE_CONSTRAINT_PRIMARYKEY
            )
            if not is_unique_violation:
                raise
            raise ConflictError(
                code="SEGMENT_EMBEDDING_ALREADY_EXISTS",
                message="Um ou mais pares (trecho, modelo) ja foram gravados.",
                details={"segment_ids": ",".join(str(item.segment_id) for item in data.embeddings)},
            ) from exc
        return [SegmentEmbeddingRead.from_model(embedding) for embedding in created]

    def search(self, demand_id: UUID, data: SimilaritySearchRequest) -> SimilaritySearchResponse:
        if self.session.get(Demand, demand_id) is None:
            raise NotFoundError(
                code="DEMAND_NOT_FOUND",
                message="Demanda nao encontrada.",
                details={"demand_id": str(demand_id)},
            )

        matches = self.repository.search_similar(
            demand_id=demand_id,
            model=data.model,
            query_vector=data.vector,
            top_k=data.top_k,
            min_similarity=data.min_similarity,
        )
        return SimilaritySearchResponse(
            results=[
                SimilaritySearchResult.from_match(segment, similarity)
                for segment, similarity in matches
            ]
        )
