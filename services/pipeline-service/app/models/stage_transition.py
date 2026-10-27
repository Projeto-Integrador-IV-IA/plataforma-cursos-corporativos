"""Registro historico de uma mudanca de etapa da demanda."""

from datetime import datetime
from typing import TYPE_CHECKING
from uuid import UUID, uuid4

import sqlalchemy as sa
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base
from app.domain.enums import PipelineStage, sql_enum_values
from app.models._append_only import forbid_changes
from app.models._types import UUID_TYPE

if TYPE_CHECKING:
    from app.models.demand import Demand
    from app.models.user import User


class StageTransition(Base):
    """Evento append-only que preserva origem, destino, autor e instante.

    A garantia tem duas camadas. Aqui, os eventos ``before_update`` e
    ``before_delete`` (no fim do modulo) recusam a operacao pelo ORM, com erro
    claro. No banco, os gatilhos da migration ``20261020_1200`` recusam qualquer
    UPDATE ou DELETE, inclusive os em massa que o ORM nao intercepta.
    """

    __tablename__ = "stage_transitions"
    __table_args__ = (
        sa.CheckConstraint(
            f"from_stage IS NULL OR from_stage IN ({sql_enum_values(PipelineStage)})",
            name="from_stage",
        ),
        sa.CheckConstraint(
            f"to_stage IN ({sql_enum_values(PipelineStage)})",
            name="to_stage",
        ),
        sa.CheckConstraint(
            "from_stage IS NULL OR from_stage <> to_stage",
            name="distinct_stages",
        ),
        sa.Index(
            "ix_stage_transitions_demand_occurred_at",
            "demand_id",
            "occurred_at",
        ),
        sa.Index("ix_stage_transitions_author_id", "author_id"),
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
            name="fk_stage_transitions_demand_id_demands",
            ondelete="RESTRICT",
        ),
        nullable=False,
    )
    from_stage: Mapped[str | None] = mapped_column(sa.Text, nullable=True)
    to_stage: Mapped[str] = mapped_column(sa.Text, nullable=False)
    reason: Mapped[str | None] = mapped_column(sa.Text, nullable=True)
    author_id: Mapped[UUID] = mapped_column(
        UUID_TYPE,
        sa.ForeignKey(
            "users.id",
            name="fk_stage_transitions_author_id_users",
            ondelete="RESTRICT",
        ),
        nullable=False,
    )
    occurred_at: Mapped[datetime] = mapped_column(
        sa.DateTime(timezone=True),
        nullable=False,
        server_default=sa.func.now(),
    )

    demand: Mapped["Demand"] = relationship(back_populates="stage_transitions")
    author: Mapped["User"] = relationship(back_populates="stage_transitions")


forbid_changes(StageTransition, "stage_transitions")
