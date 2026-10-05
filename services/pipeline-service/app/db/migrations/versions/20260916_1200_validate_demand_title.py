"""Impede titulo vazio na criacao de demandas (RF02).

O schema inicial ja define todos os campos da negociacao e client_id NOT NULL
com ON DELETE RESTRICT (RNF14 no DOCX, RNF08 na matriz do repositorio).
Esta revisao incremental completa a validacao do titulo sem recriar o dominio
ou alterar dados historicos. Titulos vazios existentes devem ser corrigidos
antes do upgrade.
"""

from collections.abc import Sequence

from alembic import op

revision: str = "20260916_1200"
down_revision: str | None = "20260902_1200"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """Exige titulo preenchido; preserva vinculos obrigatorios ja existentes."""

    with op.batch_alter_table("demands") as batch_op:
        batch_op.create_check_constraint(
            op.f("ck_demands_title_not_blank"), "length(trim(title)) > 0"
        )


def downgrade() -> None:
    """Remove somente a validacao adicionada por esta revisao."""

    with op.batch_alter_table("demands") as batch_op:
        batch_op.drop_constraint(op.f("ck_demands_title_not_blank"), type_="check")
