"""Embedding de trecho citavel, para busca por similaridade (RNF28 consolidado, ADR-0007)."""

from datetime import datetime
from typing import TYPE_CHECKING
from uuid import UUID

import sqlalchemy as sa
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base
from app.models._types import UUID_TYPE, VECTOR_TYPE

if TYPE_CHECKING:
    from app.models.raw_input import SourceSegment


class SegmentEmbedding(Base):
    """Vetor de um trecho, gerado por um modelo de embedding (card #160).

    Chave composta ``(segment_id, model)``: um mesmo trecho pode ter mais de
    um embedding, um por modelo, sem que o mais novo apague o mais antigo -
    trocar de modelo (dimensao ou qualidade diferentes) soma uma linha nova em
    vez de sobrescrever a existente, a mesma lógica append-only do restante do
    projeto (RNF09). A busca por similaridade (card #159) sempre filtra por um
    ``model`` so, nunca mistura vetores de modelos diferentes no mesmo
    ranking - distancias de modelos diferentes nao sao comparaveis.

    Sem ``author_id``: quem gera o embedding e sempre o ``ai-structuring-service``,
    nunca uma pessoa; nao ha o que a origem precise distinguir aqui.
    """

    __tablename__ = "segment_embeddings"
    __table_args__ = (sa.CheckConstraint("length(trim(model)) > 0", name="model_not_blank"),)

    segment_id: Mapped[UUID] = mapped_column(
        UUID_TYPE,
        sa.ForeignKey(
            "source_segments.id",
            name="fk_segment_embeddings_segment_id_source_segments",
            ondelete="RESTRICT",
        ),
        primary_key=True,
    )
    model: Mapped[str] = mapped_column(sa.Text, primary_key=True)
    vector: Mapped[list[float]] = mapped_column(VECTOR_TYPE, nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        sa.DateTime(timezone=True),
        nullable=False,
        server_default=sa.func.now(),
    )

    segment: Mapped["SourceSegment"] = relationship(back_populates="embeddings")
