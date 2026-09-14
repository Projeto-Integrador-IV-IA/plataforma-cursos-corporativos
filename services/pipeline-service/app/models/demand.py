"""Demanda comercial que percorre as etapas do pipeline."""

from datetime import datetime
from typing import TYPE_CHECKING
from uuid import UUID, uuid4

import sqlalchemy as sa
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base
from app.domain.enums import DemandStatus, PipelineStage, sql_enum_values
from app.models._types import UUID_TYPE

if TYPE_CHECKING:
    from app.models.artifact import Artifact
    from app.models.client import Client
    from app.models.raw_input import RawInput
    from app.models.stage_transition import StageTransition
    from app.models.user import User


class Demand(Base):
    """Negociacao obrigatoriamente pertencente a um cliente."""

    __tablename__ = "demands"
    __table_args__ = (
        sa.CheckConstraint(
            f"current_stage IN ({sql_enum_values(PipelineStage)})",
            name="current_stage",
        ),
        sa.CheckConstraint(
            f"status IN ({sql_enum_values(DemandStatus)})",
            name="status",
        ),
        sa.Index("ix_demands_client_status_created_at", "client_id", "status", "created_at"),
        sa.Index("ix_demands_current_stage", "current_stage"),
        sa.Index("ix_demands_owner_id", "owner_id"),
    )

    id: Mapped[UUID] = mapped_column(
        UUID_TYPE,
        primary_key=True,
        default=uuid4,
        server_default=sa.text("gen_random_uuid()"),
    )
    client_id: Mapped[UUID] = mapped_column(
        UUID_TYPE,
        sa.ForeignKey(
            "clients.id",
            name="fk_demands_client_id_clients",
            ondelete="RESTRICT",
        ),
        nullable=False,
    )
    title: Mapped[str] = mapped_column(sa.Text, nullable=False)
    description: Mapped[str | None] = mapped_column(sa.Text, nullable=True)
    current_stage: Mapped[str] = mapped_column(
        sa.Text,
        nullable=False,
        default=PipelineStage.CAPTACAO.value,
        server_default=sa.text(f"'{PipelineStage.CAPTACAO.value}'"),
    )
    status: Mapped[str] = mapped_column(
        sa.Text,
        nullable=False,
        default=DemandStatus.ABERTA.value,
        server_default=sa.text(f"'{DemandStatus.ABERTA.value}'"),
    )
    owner_id: Mapped[UUID | None] = mapped_column(
        UUID_TYPE,
        sa.ForeignKey(
            "users.id",
            name="fk_demands_owner_id_users",
            ondelete="RESTRICT",
        ),
        nullable=True,
    )
    active: Mapped[bool] = mapped_column(
        sa.Boolean,
        nullable=False,
        default=True,
        server_default=sa.true(),
    )
    created_at: Mapped[datetime] = mapped_column(
        sa.DateTime(timezone=True),
        nullable=False,
        server_default=sa.func.now(),
    )
    updated_at: Mapped[datetime] = mapped_column(
        sa.DateTime(timezone=True),
        nullable=False,
        server_default=sa.func.now(),
    )

    client: Mapped["Client"] = relationship(back_populates="demands")
    owner: Mapped["User | None"] = relationship(
        back_populates="owned_demands",
        foreign_keys=[owner_id],
    )
    raw_inputs: Mapped[list["RawInput"]] = relationship(
        back_populates="demand",
        passive_deletes=True,
    )
    stage_transitions: Mapped[list["StageTransition"]] = relationship(
        back_populates="demand",
        passive_deletes=True,
    )
    artifacts: Mapped[list["Artifact"]] = relationship(
        back_populates="demand",
        passive_deletes=True,
    )
