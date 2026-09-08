"""Empresa cliente vinculada as demandas comerciais."""

from datetime import datetime
from typing import TYPE_CHECKING
from uuid import UUID, uuid4

import sqlalchemy as sa
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base
from app.models._types import UUID_TYPE

if TYPE_CHECKING:
    from app.models.demand import Demand


class Client(Base):
    """Cliente com inativacao logica e CNPJ unico quando informado."""

    __tablename__ = "clients"
    __table_args__ = (sa.UniqueConstraint("cnpj", name="uq_clients_cnpj"),)

    id: Mapped[UUID] = mapped_column(
        UUID_TYPE,
        primary_key=True,
        default=uuid4,
        server_default=sa.text("gen_random_uuid()"),
    )
    name: Mapped[str] = mapped_column(sa.Text, nullable=False)
    cnpj: Mapped[str | None] = mapped_column(sa.Text, nullable=True)
    segment: Mapped[str | None] = mapped_column(sa.Text, nullable=True)
    contact_name: Mapped[str | None] = mapped_column(sa.Text, nullable=True)
    contact_email: Mapped[str | None] = mapped_column(sa.Text, nullable=True)
    contact_phone: Mapped[str | None] = mapped_column(sa.Text, nullable=True)
    notes: Mapped[str | None] = mapped_column(sa.Text, nullable=True)
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

    demands: Mapped[list["Demand"]] = relationship(
        back_populates="client",
        passive_deletes=True,
    )
