"""Arquivo original imutavel, no mesmo banco e transacao da fonte RF30."""

from typing import TYPE_CHECKING
from uuid import UUID

import sqlalchemy as sa
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base
from app.models._append_only import forbid_changes
from app.models._types import UUID_TYPE

if TYPE_CHECKING:
    from app.models.raw_input import RawInput


class AudioInput(Base):
    __tablename__ = "audio_inputs"
    __table_args__ = (
        sa.CheckConstraint("size_bytes > 0 AND length(content) = size_bytes", name="size_valid"),
        sa.CheckConstraint("duration_seconds > 0", name="duration_positive"),
        sa.CheckConstraint("length(sha256) = 64", name="sha256_length"),
    )

    raw_input_id: Mapped[UUID] = mapped_column(
        UUID_TYPE, sa.ForeignKey("raw_inputs.id", ondelete="RESTRICT"), primary_key=True
    )
    filename: Mapped[str] = mapped_column(sa.String(255), nullable=False)
    content_type: Mapped[str] = mapped_column(sa.String(64), nullable=False)
    size_bytes: Mapped[int] = mapped_column(sa.Integer, nullable=False)
    duration_seconds: Mapped[float] = mapped_column(sa.Float, nullable=False)
    sha256: Mapped[str] = mapped_column(sa.String(64), nullable=False)
    content: Mapped[bytes] = mapped_column(sa.LargeBinary, nullable=False, deferred=True)
    raw_input: Mapped["RawInput"] = relationship(back_populates="audio")


forbid_changes(AudioInput, "audio_inputs")
