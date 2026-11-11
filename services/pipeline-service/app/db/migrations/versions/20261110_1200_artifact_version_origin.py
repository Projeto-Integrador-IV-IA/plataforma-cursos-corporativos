"""Liga revisoes humanas a versao de IA que as originou (RF14/RF08)."""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "20261110_1200"
down_revision: str | None = "20261025_1200"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """Adiciona ponteiro imutavel para a versao original gerada pela IA."""

    with op.batch_alter_table("artifact_versions") as batch_op:
        batch_op.add_column(sa.Column("origin_number", sa.Integer(), nullable=True))
        batch_op.create_check_constraint(
            op.f("ck_artifact_versions_origin_before_self"),
            "origin_number IS NULL OR origin_number < number",
        )
        batch_op.create_foreign_key(
            "fk_artifact_versions_origin",
            "artifact_versions",
            ["artifact_id", "origin_number"],
            ["artifact_id", "number"],
            ondelete="RESTRICT",
        )

    op.create_index(
        "ix_artifact_versions_origin", "artifact_versions", ["artifact_id", "origin_number"]
    )

    # SQLite recria a tabela em batch_alter_table e perde os gatilhos da
    # migration append-only; restaura-os nesta mesma migration.
    _create_append_only_triggers_if_sqlite()


def downgrade() -> None:
    """Remove somente o ponteiro da origem."""

    op.drop_index("ix_artifact_versions_origin", table_name="artifact_versions")
    with op.batch_alter_table("artifact_versions") as batch_op:
        batch_op.drop_constraint("fk_artifact_versions_origin", type_="foreignkey")
        batch_op.drop_constraint(op.f("ck_artifact_versions_origin_before_self"), type_="check")
        batch_op.drop_column("origin_number")
    # O batch do SQLite recria a tabela e remove os gatilhos. Eles pertencem
    # a 20261022_1300, portanto devem existir para que essa migration anterior
    # possa removê-los no passo seguinte do downgrade.
    _create_append_only_triggers_if_sqlite()


def _create_append_only_triggers_if_sqlite() -> None:
    if op.get_bind().dialect.name != "sqlite":
        return
    op.execute(
        "CREATE TRIGGER trg_artifact_versions_refuse_update "
        "BEFORE UPDATE ON artifact_versions BEGIN SELECT RAISE(ABORT, "
        "'artifact_versions e append-only - UPDATE nao e permitido'); END"
    )
    op.execute(
        "CREATE TRIGGER trg_artifact_versions_refuse_delete "
        "BEFORE DELETE ON artifact_versions BEGIN SELECT RAISE(ABORT, "
        "'artifact_versions e append-only - DELETE nao e permitido'); END"
    )
