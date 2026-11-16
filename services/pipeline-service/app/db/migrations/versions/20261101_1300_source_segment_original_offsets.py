"""Guarda os offsets dos trechos no conteudo original (RF27, #152)."""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "20261101_1300"
down_revision: str | None = "20261101_1200"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column("source_segments", sa.Column("original_start_offset", sa.Integer()))
    op.add_column("source_segments", sa.Column("original_end_offset", sa.Integer()))

    connection = op.get_bind()
    rows = (
        connection.execute(
            sa.text(
                """
            SELECT source_segments.id, source_segments.raw_input_id,
                   source_segments.content, raw_inputs.original_content
            FROM source_segments
            JOIN raw_inputs ON raw_inputs.id = source_segments.raw_input_id
            ORDER BY source_segments.raw_input_id, source_segments.position
            """
            )
        )
        .mappings()
        .all()
    )
    cursor_by_source: dict[object, int] = {}
    for row in rows:
        original = row["original_content"]
        content = row["content"]
        cursor = cursor_by_source.get(row["raw_input_id"], 0)
        start = original.find(content, cursor)
        if start < 0:
            start = original.find(content)
        if start < 0:
            continue
        end = start + len(content)
        connection.execute(
            sa.text(
                """
                UPDATE source_segments
                SET original_start_offset = :start, original_end_offset = :end
                WHERE id = :id
                """
            ),
            {"id": row["id"], "start": start, "end": end},
        )
        cursor_by_source[row["raw_input_id"]] = end

    with op.batch_alter_table("source_segments") as batch_op:
        batch_op.create_check_constraint(
            op.f("ck_source_segments_original_offsets_valid"),
            "(original_start_offset IS NULL AND original_end_offset IS NULL) OR "
            "(original_start_offset >= 0 AND original_end_offset > original_start_offset)",
        )


def downgrade() -> None:
    with op.batch_alter_table("source_segments") as batch_op:
        batch_op.drop_constraint(op.f("ck_source_segments_original_offsets_valid"), type_="check")
        batch_op.drop_column("original_end_offset")
        batch_op.drop_column("original_start_offset")
