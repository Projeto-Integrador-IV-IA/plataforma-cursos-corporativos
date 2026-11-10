"""Vincula edicoes humanas a versao IA de origem (RF19.1).

Revision ID: 20261109_1200
Revises: 20261101_1300

Versoes existentes permanecem intactas. No SQLite, o batch recria a tabela;
os gatilhos append-only precisam ser reinstalados apos upgrade e downgrade.
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "20261109_1200"
down_revision: str | None = "20261101_1300"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def _restore_sqlite_triggers() -> None:
    if op.get_bind().dialect.name == "sqlite":
        # SQL local: migrations devem funcionar sem depender do estado Python
        # de outras revisoes, inclusive quando executadas pelo andaime de testes.
        for suffix, operation in (("update", "UPDATE"), ("delete", "DELETE")):
            op.execute(
                f"CREATE TRIGGER trg_artifact_versions_refuse_{suffix} "
                f"BEFORE {operation} ON artifact_versions "
                f"BEGIN SELECT RAISE(ABORT, 'artifact_versions e append-only - "
                f"{operation} nao e permitido'); END"
            )


def upgrade() -> None:
    with op.batch_alter_table("artifact_versions") as batch:
        batch.add_column(sa.Column("ai_origin_number", sa.Integer(), nullable=True))
        batch.create_check_constraint(
            op.f("ck_artifact_versions_ai_origin_before_self"),
            "ai_origin_number IS NULL OR (ai_origin_number > 0 AND ai_origin_number < number)",
        )
        batch.create_foreign_key(
            "fk_artifact_versions_ai_origin",
            "artifact_versions",
            ["artifact_id", "ai_origin_number"],
            ["artifact_id", "number"],
            ondelete="RESTRICT",
        )
    op.create_index(
        "ix_artifact_versions_ai_origin", "artifact_versions", ["artifact_id", "ai_origin_number"]
    )
    _restore_sqlite_triggers()


def downgrade() -> None:
    op.drop_index("ix_artifact_versions_ai_origin", table_name="artifact_versions")
    with op.batch_alter_table("artifact_versions") as batch:
        batch.drop_constraint("fk_artifact_versions_ai_origin", type_="foreignkey")
        batch.drop_constraint(op.f("ck_artifact_versions_ai_origin_before_self"), type_="check")
        batch.drop_column("ai_origin_number")
    _restore_sqlite_triggers()
