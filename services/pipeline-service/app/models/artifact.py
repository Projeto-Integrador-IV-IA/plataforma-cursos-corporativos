"""Artefatos logicos e suas versoes imutaveis."""

from datetime import datetime
from typing import TYPE_CHECKING, Any
from uuid import UUID, uuid4

import sqlalchemy as sa
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base
from app.domain.enums import ArtifactOrigin, ArtifactType, sql_enum_values
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
            f"type IN ({sql_enum_values(ArtifactType)})",
            name="type",
        ),
        sa.ForeignKeyConstraint(
            ["raw_input_id", "demand_id"],
            ["raw_inputs.id", "raw_inputs.demand_id"],
            name="fk_artifacts_raw_input_demand",
            ondelete="RESTRICT",
        ),
        sa.Index("ix_artifacts_demand_id", "demand_id"),
        sa.Index("ix_artifacts_raw_input_demand", "raw_input_id", "demand_id"),
        sa.UniqueConstraint("id", "demand_id", name="uq_artifacts_id_demand_id"),
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
    source_links: Mapped[list["ArtifactSource"]] = relationship(
        back_populates="artifact",
        cascade="all, delete-orphan",
        order_by="ArtifactSource.raw_input_id",
    )


class ArtifactVersion(Base):
    """Versao append-only do conteudo de um artefato."""

    __tablename__ = "artifact_versions"
    __table_args__ = (
        sa.CheckConstraint("number > 0", name="number_positive"),
        sa.CheckConstraint(
            f"origin = '{ArtifactOrigin.IA.value}' OR author_id IS NOT NULL",
            name="human_requires_author",
        ),
        sa.CheckConstraint(
            f"origin <> '{ArtifactOrigin.IA.value}' OR raw_content IS NOT NULL",
            name="ia_requires_raw_content",
        ),
        sa.CheckConstraint(
            f"origin IN ({sql_enum_values(ArtifactOrigin)})",
            name="origin",
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
    # Nulo de proposito na versao humana: quem editou na revisao (RF14) nao tem
    # saida bruta de modelo, e gravar "" seria registrar uma resposta que nunca
    # existiu. O CHECK acima exige o bruto quando a origem e a IA.
    raw_content: Mapped[str | None] = mapped_column(sa.Text, nullable=True)
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


class ArtifactSource(Base):
    """Fonte usada pela IA, vinculada ao artefato dentro da mesma demanda."""

    __tablename__ = "artifact_sources"
    __table_args__ = (
        sa.ForeignKeyConstraint(
            ["artifact_id", "demand_id"],
            ["artifacts.id", "artifacts.demand_id"],
            name="fk_artifact_sources_artifact_demand",
            ondelete="RESTRICT",
        ),
        sa.ForeignKeyConstraint(
            ["raw_input_id", "demand_id"],
            ["raw_inputs.id", "raw_inputs.demand_id"],
            name="fk_artifact_sources_raw_input_demand",
            ondelete="RESTRICT",
        ),
        sa.Index("ix_artifact_sources_demand_id", "demand_id"),
    )

    artifact_id: Mapped[UUID] = mapped_column(UUID_TYPE, primary_key=True)
    raw_input_id: Mapped[UUID] = mapped_column(UUID_TYPE, primary_key=True)
    demand_id: Mapped[UUID] = mapped_column(UUID_TYPE, nullable=False)

    artifact: Mapped[Artifact] = relationship(back_populates="source_links")
    raw_input: Mapped["RawInput"] = relationship(
        back_populates="artifact_source_links",
        viewonly=True,
    )
