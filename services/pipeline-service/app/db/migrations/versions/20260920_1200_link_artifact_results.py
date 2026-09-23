"""Vincula resultado bruto, estruturado e todas as fontes usadas (RF16.1)."""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

from app.models._types import UUID_TYPE

revision: str = "20260920_1200"
down_revision: str | None = "20260916_1200"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """Acrescenta o bruto da IA e a associacao N:N protegida por demanda."""

    with op.batch_alter_table("artifacts") as batch_op:
        batch_op.create_unique_constraint(
            "uq_artifacts_id_demand_id",
            ["id", "demand_id"],
        )

    # Nulo e permitido: a versao criada na revisao humana (RF14) nao tem saida
    # bruta de modelo. O CHECK cobra o bruto apenas quando a origem e a IA.
    with op.batch_alter_table("artifact_versions") as batch_op:
        batch_op.add_column(sa.Column("raw_content", sa.Text(), nullable=True))
        batch_op.create_check_constraint(
            op.f("ck_artifact_versions_ia_requires_raw_content"),
            "origin <> 'IA' OR raw_content IS NOT NULL",
        )

    op.create_table(
        "artifact_sources",
        sa.Column("artifact_id", UUID_TYPE, nullable=False),
        sa.Column("raw_input_id", UUID_TYPE, nullable=False),
        sa.Column("demand_id", UUID_TYPE, nullable=False),
        sa.ForeignKeyConstraint(
            ["artifact_id", "demand_id"],
            ["artifacts.id", "artifacts.demand_id"],
            name="fk_artifact_sources_artifact_demand",
            ondelete="RESTRICT",
        ),
        sa.ForeignKeyConstraint(
            ["raw_input_id", "demand_id"],
            ["raw_inputs.id", "raw_inputs.demand_id"],
            name="fk_artifact_sources_raw_input_demand",
            ondelete="RESTRICT",
        ),
        sa.PrimaryKeyConstraint(
            "artifact_id",
            "raw_input_id",
            name=op.f("pk_artifact_sources"),
        ),
    )
    op.create_index(
        "ix_artifact_sources_demand_id",
        "artifact_sources",
        ["demand_id"],
    )


def downgrade() -> None:
    """Remove apenas os campos e vinculos introduzidos nesta revisao."""

    op.drop_index("ix_artifact_sources_demand_id", table_name="artifact_sources")
    op.drop_table("artifact_sources")

    with op.batch_alter_table("artifact_versions") as batch_op:
        batch_op.drop_constraint(
            op.f("ck_artifact_versions_ia_requires_raw_content"), type_="check"
        )
        batch_op.drop_column("raw_content")

    with op.batch_alter_table("artifacts") as batch_op:
        batch_op.drop_constraint("uq_artifacts_id_demand_id", type_="unique")
