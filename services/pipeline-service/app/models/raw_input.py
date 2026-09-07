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
    from app.models.artifact import Artifact
    from app.models.demand import Demand
    from app.models.user import User


class RawInput(Base):
    """Conteudo original preservado antes da normalizacao ou do LLM."""

    __tablename__ = "raw_inputs"
    __table_args__ = (
        sa.CheckConstraint(
            f"source IN ({sql_enum_values(RawInputSource)})",
            name="source",
        ),
        sa.UniqueConstraint("id", "demand_id", name="uq_raw_inputs_id_demand_id"),
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
    artifacts: Mapped[list["Artifact"]] = relationship(
        back_populates="raw_input",
        primaryjoin="RawInput.id == Artifact.raw_input_id",
        foreign_keys="Artifact.raw_input_id",
        passive_deletes=True,
    )
