"""Liga cada versao de artefato a sua antecessora (RF08).

Revision ID: 20261022_1200
Revises: 20261021_1200

``previous_number`` aponta para a versao de numero imediatamente menor do mesmo
artefato e e nulo so na primeira. A chave estrangeira composta garante que a
antecessora existe e e do mesmo artefato; o CHECK, que e exatamente a anterior.
Versoes ja gravadas sao preenchidas pelo proprio numero. Se algum artefato tiver
buraco na numeracao (por exemplo, 1 e 3), o CHECK falha e a migration para: o
buraco precisa ser corrigido antes.
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "20261022_1200"
down_revision: str | None = "20261021_1200"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """Acrescenta a coluna, preenche as versoes existentes e so entao a protege."""

    with op.batch_alter_table("artifact_versions") as batch_op:
        batch_op.add_column(sa.Column("previous_number", sa.Integer(), nullable=True))

    op.execute("UPDATE artifact_versions SET previous_number = number - 1 WHERE number > 1")

    with op.batch_alter_table("artifact_versions") as batch_op:
        # COALESCE porque NULL num CHECK passaria como "ok": sem ele, a versao 2
        # sem antecessora seria aceita.
        batch_op.create_check_constraint(
            op.f("ck_artifact_versions_previous_is_predecessor"),
            "COALESCE(previous_number, 0) = number - 1",
        )
        batch_op.create_foreign_key(
            "fk_artifact_versions_previous",
            "artifact_versions",
            ["artifact_id", "previous_number"],
            ["artifact_id", "number"],
            ondelete="RESTRICT",
        )

    op.create_index(
        "ix_artifact_versions_previous",
        "artifact_versions",
        ["artifact_id", "previous_number"],
    )


def downgrade() -> None:
    """Remove somente o vinculo com a versao anterior."""

    op.drop_index("ix_artifact_versions_previous", table_name="artifact_versions")

    with op.batch_alter_table("artifact_versions") as batch_op:
        batch_op.drop_constraint("fk_artifact_versions_previous", type_="foreignkey")
        batch_op.drop_constraint(
            op.f("ck_artifact_versions_previous_is_predecessor"), type_="check"
        )
        batch_op.drop_column("previous_number")
