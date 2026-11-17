"""Preserva arquivos de audio com a proveniencia da fonte (RF30, #164)."""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "20261110_1200"
down_revision: str | None = "20261101_1300"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

SOURCES = "'EMAIL', 'TRANSCRICAO', 'MENSAGENS', 'ANOTACAO', 'OUTRO'"


def upgrade() -> None:
    with op.batch_alter_table("raw_inputs") as batch:
        batch.drop_constraint(op.f("ck_raw_inputs_source"), type_="check")
        batch.create_check_constraint(
            op.f("ck_raw_inputs_source"), f"source IN ({SOURCES}, 'AUDIO')"
        )
    op.create_table(
        "audio_inputs",
        sa.Column("raw_input_id", sa.Uuid(), nullable=False),
        sa.Column("filename", sa.String(255), nullable=False),
        sa.Column("content_type", sa.String(64), nullable=False),
        sa.Column("size_bytes", sa.Integer(), nullable=False),
        sa.Column("duration_seconds", sa.Float(), nullable=False),
        sa.Column("sha256", sa.String(64), nullable=False),
        sa.Column("content", sa.LargeBinary(), nullable=False),
        sa.PrimaryKeyConstraint("raw_input_id", name="pk_audio_inputs"),
        sa.ForeignKeyConstraint(
            ["raw_input_id"],
            ["raw_inputs.id"],
            ondelete="RESTRICT",
            name="fk_audio_inputs_raw_input_id_raw_inputs",
        ),
        sa.CheckConstraint(
            "size_bytes > 0 AND length(content) = size_bytes",
            name=op.f("ck_audio_inputs_size_valid"),
        ),
        sa.CheckConstraint("duration_seconds > 0", name=op.f("ck_audio_inputs_duration_positive")),
        sa.CheckConstraint("length(sha256) = 64", name=op.f("ck_audio_inputs_sha256_length")),
    )
    if op.get_bind().dialect.name == "postgresql":
        op.execute("""
            CREATE FUNCTION protect_audio_original() RETURNS trigger LANGUAGE plpgsql AS $$
            BEGIN RAISE EXCEPTION 'audio_inputs e imutavel'; END; $$
        """)
        op.execute("""
            CREATE TRIGGER audio_original_immutable BEFORE UPDATE OR DELETE ON audio_inputs
            FOR EACH ROW EXECUTE FUNCTION protect_audio_original()
        """)
    else:
        for operation in ("UPDATE", "DELETE"):
            op.execute(f"""
                CREATE TRIGGER audio_original_{operation.lower()} BEFORE {operation} ON audio_inputs
                BEGIN SELECT RAISE(ABORT, 'audio_inputs e imutavel'); END
            """)


def downgrade() -> None:
    if op.get_bind().scalar(sa.text("SELECT count(*) FROM raw_inputs WHERE source = 'AUDIO'")):
        raise RuntimeError(
            "Downgrade recusado: existem fontes AUDIO; preserve os arquivos e metadados."
        )
    op.drop_table("audio_inputs")
    if op.get_bind().dialect.name == "postgresql":
        op.execute("DROP FUNCTION protect_audio_original()")
    with op.batch_alter_table("raw_inputs") as batch:
        batch.drop_constraint(op.f("ck_raw_inputs_source"), type_="check")
        batch.create_check_constraint(op.f("ck_raw_inputs_source"), f"source IN ({SOURCES})")
