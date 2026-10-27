"""Registra a ordem de recebimento por demanda (RF10, #32)."""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "20261025_1200"
down_revision: str | None = "20261022_1300"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """Numera o legado sem alterar conteudo, origem, autor ou data."""

    op.add_column("raw_inputs", sa.Column("received_order", sa.Integer(), nullable=True))
    # Empates historicos nao permitem recuperar a chegada real. UUID fornece
    # somente um desempate deterministico para os registros anteriores ao RF10.
    op.execute(
        sa.text("""
        WITH ranked AS (
            SELECT id, ROW_NUMBER() OVER (
                PARTITION BY demand_id ORDER BY created_at, id
            ) AS position
            FROM raw_inputs
        )
        UPDATE raw_inputs SET received_order = (
            SELECT position FROM ranked WHERE ranked.id = raw_inputs.id
        )
    """)
    )
    with op.batch_alter_table("raw_inputs") as batch_op:
        batch_op.alter_column("received_order", existing_type=sa.Integer(), nullable=False)
        batch_op.create_unique_constraint(
            "uq_raw_inputs_demand_received_order", ["demand_id", "received_order"]
        )
        batch_op.create_check_constraint(
            op.f("ck_raw_inputs_received_order_positive"), "received_order > 0"
        )


def downgrade() -> None:
    """Remove apenas a sequencia, preservando as fontes."""

    with op.batch_alter_table("raw_inputs") as batch_op:
        batch_op.drop_constraint("uq_raw_inputs_demand_received_order", type_="unique")
        batch_op.drop_constraint(op.f("ck_raw_inputs_received_order_positive"), type_="check")
        batch_op.drop_column("received_order")
