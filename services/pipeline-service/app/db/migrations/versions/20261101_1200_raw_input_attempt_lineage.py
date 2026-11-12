"""Vincula reprocessamentos a tentativas anteriores (RF12, #36)."""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

from app.models._types import UUID_TYPE

revision: str = "20261101_1200"
down_revision: str | None = "20261025_1200"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column("raw_inputs", sa.Column("previous_attempt_id", UUID_TYPE, nullable=True))
    with op.batch_alter_table("raw_inputs") as batch_op:
        batch_op.create_foreign_key(
            "fk_raw_inputs_previous_attempt_same_demand",
            "raw_inputs",
            ["previous_attempt_id", "demand_id"],
            ["id", "demand_id"],
            ondelete="RESTRICT",
        )
        batch_op.create_index("ix_raw_inputs_previous_attempt_id", ["previous_attempt_id"])


def downgrade() -> None:
    with op.batch_alter_table("raw_inputs") as batch_op:
        batch_op.drop_index("ix_raw_inputs_previous_attempt_id")
        batch_op.drop_constraint("fk_raw_inputs_previous_attempt_same_demand", type_="foreignkey")
        batch_op.drop_column("previous_attempt_id")
