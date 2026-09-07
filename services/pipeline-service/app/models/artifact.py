"""Artefatos logicos e suas versoes imutaveis."""

from datetime import datetime
from typing import TYPE_CHECKING, Any
from uuid import UUID, uuid4

import sqlalchemy as sa
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base
from app.models._types import JSON_TYPE, UUID_TYPE

if TYPE_CHECKING:
    from app.models.demand import Demand
    from app.models.raw_input import RawInput
    from app.models.user import User


class Artifact(Base):
    """Documento logico vinculado a demanda e, opcionalmente, a fonte."""

    __tablename__ = "artifacts"
    __table_args__ = (
        sa.CheckConstraint(
            "type IN ('DEMANDA_BRUTA', 'REQUISITOS_EXTRAIDOS', 'EMENTA', 'PROPOSTA', 'OUTRO')",
            name="ck_artifacts_type",
        ),
        sa.ForeignKeyConstraint(
            ["raw_input_id", "demand_id"],
            ["raw_inputs.id", "raw_inputs.demand_id"],
            name="fk_artifacts_raw_input_demand",
            ondelete="RESTRICT",
        ),
        sa.Index("ix_artifacts_demand_id", "demand_id"),
        sa.Index("ix_artifacts_raw_input_demand", "raw_input_id", "demand_id"),
    )

    id: Mapped[UUID] = mapped_column(
        UUID_TYPE,
        primary_key=True,
        default=uuid4,
        server_default=sa.text("gen_random_uuid()"),
    )
    demand_id: Mapped[UUID] = mapped_column(
        UUID_TYPE,
        sa.ForeignKey(
            "demands.id",
            name="fk_artifacts_demand_id_demands",
            ondelete="RESTRICT",
        ),
        nullable=False,
    )
    type: Mapped[str] = mapped_column(sa.Text, nullable=False)
    title: Mapped[str | None] = mapped_column(sa.Text, nullable=True)
    raw_input_id: Mapped[UUID | None] = mapped_column(UUID_TYPE, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        sa.DateTime(timezone=True),
        nullable=False,
        server_default=sa.func.now(),
    )

    demand: Mapped["Demand"] = relationship(back_populates="artifacts")
    raw_input: Mapped["RawInput | None"] = relationship(
        back_populates="artifacts",
        primaryjoin="Artifact.raw_input_id == RawInput.id",
        foreign_keys=[raw_input_id],
    )
    versions: Mapped[list["ArtifactVersion"]] = relationship(
        back_populates="artifact",
        passive_deletes=True,
        order_by="ArtifactVersion.number",
    )


class ArtifactVersion(Base):
    """Versao append-only do conteudo de um artefato."""

    __tablename__ = "artifact_versions"
    __table_args__ = (
        sa.CheckConstraint("number > 0", name="ck_artifact_versions_number_positive"),
        sa.CheckConstraint(
            "origin = 'IA' OR author_id IS NOT NULL",
            name="ck_artifact_versions_human_requires_author",
        ),
        sa.CheckConstraint(
            "origin IN ('IA', 'HUMANO')",
            name="ck_artifact_versions_origin",
        ),
        sa.UniqueConstraint(
            "artifact_id",
            "number",
            name="uq_artifact_versions_number",
        ),
        sa.Index("ix_artifact_versions_author_id", "author_id"),
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
            name="fk_artifact_versions_artifact_id_artifacts",
            ondelete="RESTRICT",
        ),
        nullable=False,
    )
    number: Mapped[int] = mapped_column(sa.Integer, nullable=False)
    content: Mapped[dict[str, Any]] = mapped_column(JSON_TYPE, nullable=False)
    origin: Mapped[str] = mapped_column(sa.Text, nullable=False)
    ai_metadata: Mapped[dict[str, Any] | None] = mapped_column(JSON_TYPE, nullable=True)
    author_id: Mapped[UUID | None] = mapped_column(
        UUID_TYPE,
        sa.ForeignKey(
            "users.id",
            name="fk_artifact_versions_author_id_users",
            ondelete="RESTRICT",
        ),
        nullable=True,
    )
    created_at: Mapped[datetime] = mapped_column(
        sa.DateTime(timezone=True),
        nullable=False,
        server_default=sa.func.now(),
    )

    artifact: Mapped[Artifact] = relationship(back_populates="versions")
    author: Mapped["User | None"] = relationship(back_populates="artifact_versions")
