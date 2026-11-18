"""Decisao de revisao humana sobre uma versao de artefato (RF19.2)."""

from datetime import datetime
from typing import TYPE_CHECKING
from uuid import UUID, uuid4

import sqlalchemy as sa
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base
from app.domain.enums import ArtifactReviewDecision, sql_enum_values
from app.models._append_only import forbid_changes
from app.models._types import UUID_TYPE

if TYPE_CHECKING:
    from app.models.artifact import Artifact
    from app.models.user import User


class ArtifactReview(Base):
    """Evento append-only: aprovar, rejeitar ou devolver uma versao (cards #58-#60).

    A decisao e sobre uma VERSAO especifica, nao sobre o artefato em geral:
    quem revisa precisa dizer o que exatamente leu, e uma edicao humana
    posterior (RF19.1) nao pode herdar silenciosamente a aprovacao de uma
    versao anterior - o servico recusa revisar uma versao que nao e mais a
    vigente (card #60). REJEITADO e DEVOLVIDO exigem justificativa; APROVADO
    nao exige, por simetria com RF06 (retroceder exige motivo, avancar nao).

    A garantia de append-only tem duas camadas, como nas demais tabelas de
    evento (``stage_transitions``, ``artifact_versions``): aqui, pelo ORM; no
    banco, pelos gatilhos desta mesma migration.
    """

    __tablename__ = "artifact_reviews"
    __table_args__ = (
        sa.CheckConstraint(
            f"decision IN ({sql_enum_values(ArtifactReviewDecision)})",
            name="decision",
        ),
        sa.CheckConstraint(
            f"decision = '{ArtifactReviewDecision.APROVADO.value}' "
            "OR (reason IS NOT NULL AND length(trim(reason)) > 0)",
            name="rejection_or_return_requires_reason",
        ),
        sa.CheckConstraint("version_number > 0", name="version_number_positive"),
        sa.ForeignKeyConstraint(
            ["artifact_id", "version_number"],
            ["artifact_versions.artifact_id", "artifact_versions.number"],
            name="fk_artifact_reviews_version",
            ondelete="RESTRICT",
        ),
        sa.Index("ix_artifact_reviews_artifact_created_at", "artifact_id", "created_at"),
        sa.Index("ix_artifact_reviews_author_id", "author_id"),
    )

    id: Mapped[UUID] = mapped_column(
        UUID_TYPE,
        primary_key=True,
        default=uuid4,
        server_default=sa.text("gen_random_uuid()"),
    )
    artifact_id: Mapped[UUID] = mapped_column(
        UUID_TYPE,
        sa.ForeignKey(
            "artifacts.id",
            name="fk_artifact_reviews_artifact_id_artifacts",
            ondelete="RESTRICT",
        ),
        nullable=False,
    )
    version_number: Mapped[int] = mapped_column(sa.Integer, nullable=False)
    decision: Mapped[str] = mapped_column(sa.Text, nullable=False)
    reason: Mapped[str | None] = mapped_column(sa.Text, nullable=True)
    author_id: Mapped[UUID] = mapped_column(
        UUID_TYPE,
        sa.ForeignKey(
            "users.id",
            name="fk_artifact_reviews_author_id_users",
            ondelete="RESTRICT",
        ),
        nullable=False,
    )
    created_at: Mapped[datetime] = mapped_column(
        sa.DateTime(timezone=True),
        nullable=False,
        server_default=sa.func.now(),
    )

    artifact: Mapped["Artifact"] = relationship(back_populates="reviews")
    author: Mapped["User"] = relationship(back_populates="artifact_reviews")


forbid_changes(ArtifactReview, "artifact_reviews")
