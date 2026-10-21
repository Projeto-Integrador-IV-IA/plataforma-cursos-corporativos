"""Registra, na propria versao, qual versao anterior ela restaura (RF08).

Revision ID: 20261021_1200
Revises: 20261020_1200

Restaurar nao desfaz: cria uma versao nova com o conteudo da escolhida. A versao
nova guarda o numero da restaurada em ``restored_from_number``; essa linha e o
evento de restauracao - qual versao voltou, quem restaurou (``author_id``) e
quando (``created_at``). A chave estrangeira composta garante que o ponteiro
aponta para uma versao do mesmo artefato, e o CHECK, que ela e anterior.
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "20261021_1200"
down_revision: str | None = "20261020_1200"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """Acrescenta o ponteiro de restauracao, com integridade e indice."""

    with op.batch_alter_table("artifact_versions") as batch_op:
        batch_op.add_column(sa.Column("restored_from_number", sa.Integer(), nullable=True))
        batch_op.create_check_constraint(
            op.f("ck_artifact_versions_restored_before_self"),
            "restored_from_number IS NULL OR restored_from_number < number",
        )
        batch_op.create_foreign_key(
            "fk_artifact_versions_restored_from",
            "artifact_versions",
            ["artifact_id", "restored_from_number"],
            ["artifact_id", "number"],
            ondelete="RESTRICT",
        )

    # Sem indice na coluna filha, cada DELETE no lado pai varreria a tabela
    # para validar o ON DELETE RESTRICT.
    op.create_index(
        "ix_artifact_versions_restored_from",
        "artifact_versions",
        ["artifact_id", "restored_from_number"],
    )


def downgrade() -> None:
    """Remove somente o ponteiro de restauracao."""

    op.drop_index("ix_artifact_versions_restored_from", table_name="artifact_versions")

    with op.batch_alter_table("artifact_versions") as batch_op:
        batch_op.drop_constraint("fk_artifact_versions_restored_from", type_="foreignkey")
        batch_op.drop_constraint(op.f("ck_artifact_versions_restored_before_self"), type_="check")
        batch_op.drop_column("restored_from_number")
