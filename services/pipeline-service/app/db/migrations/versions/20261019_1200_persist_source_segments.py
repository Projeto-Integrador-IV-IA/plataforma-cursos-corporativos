"""Persiste trechos citaveis vinculados a fonte e a demanda (issue 151)."""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

from app.models._types import UUID_TYPE

revision: str = "20261019_1200"
down_revision: str | None = "20260920_1200"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """Cria os trechos sem permitir fonte ausente, posicao invalida ou vazia."""

    op.create_table(
        "source_segments",
        sa.Column("id", UUID_TYPE, nullable=False),
        sa.Column("raw_input_id", UUID_TYPE, nullable=False),
        sa.Column("position", sa.Integer(), nullable=False),
        sa.Column("content", sa.Text(), nullable=False),
        sa.CheckConstraint(
            "length(trim(content)) > 0",
            name=op.f("ck_source_segments_content_not_blank"),
        ),
        sa.CheckConstraint(
            "position > 0",
            name=op.f("ck_source_segments_position_positive"),
        ),
        sa.ForeignKeyConstraint(
            ["raw_input_id"],
            ["raw_inputs.id"],
            name="fk_source_segments_raw_input_id_raw_inputs",
            ondelete="RESTRICT",
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_source_segments")),
        sa.UniqueConstraint(
            "raw_input_id",
            "position",
            name="uq_source_segments_raw_input_id_position",
        ),
    )


def downgrade() -> None:
    """Remove os trechos antes das fontes das quais dependem."""

    op.drop_table("source_segments")
