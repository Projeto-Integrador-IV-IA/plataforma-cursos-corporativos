"""Usuario da plataforma e autor dos registros auditaveis."""

from datetime import datetime
from typing import TYPE_CHECKING
from uuid import UUID, uuid4

import sqlalchemy as sa
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base
from app.models._types import UUID_TYPE

if TYPE_CHECKING:
    from app.models.artifact import ArtifactVersion
    from app.models.demand import Demand
    from app.models.raw_input import RawInput
    from app.models.stage_transition import StageTransition


class User(Base):
    """Operador cadastrado; a senha e persistida somente como hash."""

    __tablename__ = "users"
    __table_args__ = (
        sa.CheckConstraint("role IN ('OPERADOR')", name="ck_users_role"),
        sa.UniqueConstraint("email", name="uq_users_email"),
    )

    id: Mapped[UUID] = mapped_column(
        UUID_TYPE,
        primary_key=True,
        default=uuid4,
        server_default=sa.text("gen_random_uuid()"),
    )
    name: Mapped[str] = mapped_column(sa.Text, nullable=False)
    email: Mapped[str] = mapped_column(sa.Text, nullable=False)
    password_hash: Mapped[str] = mapped_column(sa.Text, nullable=False)
    role: Mapped[str] = mapped_column(
        sa.Text,
        nullable=False,
        default="OPERADOR",
        server_default=sa.text("'OPERADOR'"),
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

    owned_demands: Mapped[list["Demand"]] = relationship(
        back_populates="owner",
        foreign_keys="Demand.owner_id",
        passive_deletes=True,
    )
    raw_inputs: Mapped[list["RawInput"]] = relationship(
        back_populates="author",
        passive_deletes=True,
    )
    stage_transitions: Mapped[list["StageTransition"]] = relationship(
        back_populates="author",
        passive_deletes=True,
    )
    artifact_versions: Mapped[list["ArtifactVersion"]] = relationship(
        back_populates="author",
        passive_deletes=True,
    )
