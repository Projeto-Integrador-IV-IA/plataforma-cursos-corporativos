"""Fonte bruta recebida e vinculada a uma demanda."""

from datetime import datetime
from typing import TYPE_CHECKING
from uuid import UUID, uuid4

import sqlalchemy as sa
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base
from app.domain.enums import RawInputSource, sql_enum_values
from app.models._types import UUID_TYPE

if TYPE_CHECKING:
    from app.models.artifact import Artifact, ArtifactSource
    from app.models.demand import Demand
    from app.models.user import User


class RawInput(Base):
    """Conteudo original confirmado em transacao propria antes da normalizacao ou do LLM."""

    __tablename__ = "raw_inputs"
    __table_args__ = (
        sa.CheckConstraint(
            f"source IN ({sql_enum_values(RawInputSource)})",
            name="source",
        ),
        sa.UniqueConstraint("id", "demand_id", name="uq_raw_inputs_id_demand_id"),
        sa.UniqueConstraint(
            "demand_id", "received_order", name="uq_raw_inputs_demand_received_order"
        ),
        sa.CheckConstraint("received_order > 0", name="received_order_positive"),
        sa.Index("ix_raw_inputs_demand_created_at", "demand_id", "created_at"),
        sa.Index("ix_raw_inputs_author_id", "author_id"),
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
            name="fk_raw_inputs_demand_id_demands",
            ondelete="RESTRICT",
        ),
        nullable=False,
    )
    original_content: Mapped[str] = mapped_column(sa.Text, nullable=False)
    received_order: Mapped[int] = mapped_column(sa.Integer, nullable=False)
    normalized_content: Mapped[str | None] = mapped_column(sa.Text, nullable=True)
    source: Mapped[str] = mapped_column(sa.Text, nullable=False)
    truncated: Mapped[bool] = mapped_column(
        sa.Boolean,
        nullable=False,
        default=False,
        server_default=sa.false(),
    )
    author_id: Mapped[UUID] = mapped_column(
        UUID_TYPE,
        sa.ForeignKey(
            "users.id",
            name="fk_raw_inputs_author_id_users",
            ondelete="RESTRICT",
        ),
        nullable=False,
    )
    created_at: Mapped[datetime] = mapped_column(
        sa.DateTime(timezone=True),
        nullable=False,
        server_default=sa.func.now(),
    )

    demand: Mapped["Demand"] = relationship(back_populates="raw_inputs")
    author: Mapped["User"] = relationship(back_populates="raw_inputs")
    segments: Mapped[list["SourceSegment"]] = relationship(
        back_populates="raw_input",
        order_by="SourceSegment.position",
        passive_deletes=True,
    )
    artifacts: Mapped[list["Artifact"]] = relationship(
        back_populates="raw_input",
        primaryjoin="RawInput.id == Artifact.raw_input_id",
        foreign_keys="Artifact.raw_input_id",
        passive_deletes=True,
    )
    # Sem ``passive_deletes``: a relacao e somente leitura, entao nao executa
    # persistencia nenhuma e o parametro so gerava aviso do SQLAlchemy.
    artifact_source_links: Mapped[list["ArtifactSource"]] = relationship(
        back_populates="raw_input",
        viewonly=True,
    )


class SourceSegment(Base):
    """Trecho citavel, ordenado e persistido sob uma fonte bruta."""

    __tablename__ = "source_segments"
    __table_args__ = (
        sa.CheckConstraint("position > 0", name="position_positive"),
        sa.CheckConstraint("length(trim(content)) > 0", name="content_not_blank"),
        sa.UniqueConstraint(
            "raw_input_id",
            "position",
            name="uq_source_segments_raw_input_id_position",
        ),
    )

    id: Mapped[UUID] = mapped_column(UUID_TYPE, primary_key=True)
    raw_input_id: Mapped[UUID] = mapped_column(
        UUID_TYPE,
        sa.ForeignKey(
            "raw_inputs.id",
            name="fk_source_segments_raw_input_id_raw_inputs",
            ondelete="RESTRICT",
        ),
        nullable=False,
    )
    position: Mapped[int] = mapped_column(sa.Integer, nullable=False)
    content: Mapped[str] = mapped_column(sa.Text, nullable=False)

    raw_input: Mapped["RawInput"] = relationship(back_populates="segments")

    @property
    def demand_id(self) -> UUID:
        """Explicita na resposta a demanda alcancada pela fonte obrigatoria."""

        return self.raw_input.demand_id
