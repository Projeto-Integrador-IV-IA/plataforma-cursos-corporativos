"""Persistencia e busca por similaridade dos embeddings de trecho (RNF28 consolidado)."""

from uuid import UUID

import sqlalchemy as sa
from sqlalchemy.orm import Session, selectinload

from app.domain.vectors import cosseno
from app.models.raw_input import RawInput, SourceSegment
from app.models.segment_embedding import SegmentEmbedding


class SegmentEmbeddingRepository:
    def __init__(self, session: Session) -> None:
        self.session = session

    def get_segments(self, segment_ids: list[UUID]) -> list[SourceSegment]:
        statement = sa.select(SourceSegment).where(SourceSegment.id.in_(segment_ids))
        return list(self.session.scalars(statement).all())

    def insert_batch(self, embeddings: list[SegmentEmbedding]) -> list[SegmentEmbedding]:
        """Grava os embeddings novos; nenhum existente e tocado (append-only).

        So ``flush``: o commit e da sessao da requisicao, igual aos demais
        repositorios deste servico.
        """

        self.session.add_all(embeddings)
        self.session.flush()
        for embedding in embeddings:
            self.session.refresh(embedding)
        return embeddings

    def search_similar(
        self,
        *,
        demand_id: UUID,
        model: str,
        query_vector: list[float],
        top_k: int,
        min_similarity: float,
    ) -> list[tuple[SourceSegment, float]]:
        """Trechos da demanda mais proximos do vetor de consulta, por um modelo so.

        Recorte por demanda (RNF21): o ``WHERE`` abaixo so devolve trecho cuja
        fonte pertence a ``demand_id`` - nunca cruza demanda nem cliente. A
        similaridade e calculada em Python sobre o conjunto ja filtrado (ver
        ``app/domain/vectors.py`` para a justificativa de nao usar o operador
        nativo do pgvector aqui).
        """

        statement = (
            sa.select(SegmentEmbedding)
            .join(SourceSegment, SegmentEmbedding.segment_id == SourceSegment.id)
            .join(RawInput, SourceSegment.raw_input_id == RawInput.id)
            .where(RawInput.demand_id == demand_id, SegmentEmbedding.model == model)
            .options(selectinload(SegmentEmbedding.segment))
        )
        candidatos = self.session.scalars(statement).all()

        pontuados = (
            (embedding.segment, cosseno(query_vector, embedding.vector)) for embedding in candidatos
        )
        relevantes = (
            (segmento, similaridade)
            for segmento, similaridade in pontuados
            if similaridade >= min_similarity
        )
        return sorted(relevantes, key=lambda item: item[1], reverse=True)[:top_k]
