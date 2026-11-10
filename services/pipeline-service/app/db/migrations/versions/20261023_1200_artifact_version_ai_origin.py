"""Liga a versao editada a versao da IA que originou a cadeia (RF14, RF08).

Revision ID: 20261023_1200
Revises: 20261022_1300

A correcao humana vira versao nova (Q1). ``previous_number`` ja aponta para a
versao de que a edicao partiu; ``ai_origin_number`` aponta direto para a versao
gerada pela IA que originou a cadeia, mesmo quando ha varias edicoes no meio.
E nulo nas versoes da IA. Assim "todas as correcoes humanas da versao X da IA"
e uma consulta simples.

Versoes humanas ja gravadas sao preenchidas com a versao da IA mais recente que
as antecede - exato para edicoes e restauracoes da IA mais recente, aproximado
so para a restauracao de uma versao da IA antiga com outra mais nova no meio.

Os gatilhos da migration ``20261022_1300`` recusam UPDATE, que o preenchimento
precisa fazer; por isso eles saem antes e voltam no fim. No SQLite, alem disso,
``batch_alter_table`` recria a tabela e os levaria junto.
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "20261023_1200"
down_revision: str | None = "20261022_1300"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

TABLE = "artifact_versions"
FUNCTION = "artifact_versions_refuse_change"
UPDATE_TRIGGER = "trg_artifact_versions_refuse_update"
DELETE_TRIGGER = "trg_artifact_versions_refuse_delete"
TRUNCATE_TRIGGER = "trg_artifact_versions_refuse_truncate"


def upgrade() -> None:
    """Acrescenta o vinculo com a versao da IA, preenche e o protege."""

    _drop_append_only_triggers()

    with op.batch_alter_table("artifact_versions") as batch_op:
        batch_op.add_column(sa.Column("ai_origin_number", sa.Integer(), nullable=True))

    op.execute(
        """
        UPDATE artifact_versions
        SET ai_origin_number = (
            SELECT MAX(ia.number)
            FROM artifact_versions AS ia
            WHERE ia.artifact_id = artifact_versions.artifact_id
              AND ia.origin = 'IA'
              AND ia.number < artifact_versions.number
        )
        WHERE origin <> 'IA'
        """
    )

    with op.batch_alter_table("artifact_versions") as batch_op:
        batch_op.create_check_constraint(
            op.f("ck_artifact_versions_ai_origin_before_self"),
            "ai_origin_number IS NULL OR ai_origin_number < number",
        )
        batch_op.create_check_constraint(
            op.f("ck_artifact_versions_ia_has_no_ai_origin"),
            "origin <> 'IA' OR ai_origin_number IS NULL",
        )
        batch_op.create_foreign_key(
            "fk_artifact_versions_ai_origin",
            "artifact_versions",
            ["artifact_id", "ai_origin_number"],
            ["artifact_id", "number"],
            ondelete="RESTRICT",
        )

    op.create_index(
        "ix_artifact_versions_ai_origin",
        "artifact_versions",
        ["artifact_id", "ai_origin_number"],
    )

    _create_append_only_triggers()


def downgrade() -> None:
    """Remove somente o vinculo com a versao da IA."""

    _drop_append_only_triggers()

    op.drop_index("ix_artifact_versions_ai_origin", table_name="artifact_versions")

    with op.batch_alter_table("artifact_versions") as batch_op:
        batch_op.drop_constraint("fk_artifact_versions_ai_origin", type_="foreignkey")
        batch_op.drop_constraint(op.f("ck_artifact_versions_ia_has_no_ai_origin"), type_="check")
        batch_op.drop_constraint(op.f("ck_artifact_versions_ai_origin_before_self"), type_="check")
        batch_op.drop_column("ai_origin_number")

    _create_append_only_triggers()


def _dialect() -> str:
    dialect = op.get_bind().dialect.name
    if dialect not in {"postgresql", "sqlite"}:
        raise NotImplementedError(f"gatilho append-only nao implementado para {dialect}")
    return dialect


def _drop_append_only_triggers() -> None:
    """Tira os gatilhos da ``20261022_1300``; no PostgreSQL a funcao fica."""

    if _dialect() == "postgresql":
        op.execute(f"DROP TRIGGER {TRUNCATE_TRIGGER} ON {TABLE}")
        op.execute(f"DROP TRIGGER {DELETE_TRIGGER} ON {TABLE}")
        op.execute(f"DROP TRIGGER {UPDATE_TRIGGER} ON {TABLE}")
    else:
        op.execute(f"DROP TRIGGER {DELETE_TRIGGER}")
        op.execute(f"DROP TRIGGER {UPDATE_TRIGGER}")


def _create_append_only_triggers() -> None:
    """Recria os mesmos gatilhos da ``20261022_1300``."""

    if _dialect() == "postgresql":
        op.execute(
            f"CREATE TRIGGER {UPDATE_TRIGGER} BEFORE UPDATE ON {TABLE} "
            f"FOR EACH ROW EXECUTE FUNCTION {FUNCTION}()"
        )
        op.execute(
            f"CREATE TRIGGER {DELETE_TRIGGER} BEFORE DELETE ON {TABLE} "
            f"FOR EACH ROW EXECUTE FUNCTION {FUNCTION}()"
        )
        op.execute(
            f"CREATE TRIGGER {TRUNCATE_TRIGGER} BEFORE TRUNCATE ON {TABLE} "
            f"FOR EACH STATEMENT EXECUTE FUNCTION {FUNCTION}()"
        )
    else:
        for trigger, operation in ((UPDATE_TRIGGER, "UPDATE"), (DELETE_TRIGGER, "DELETE")):
            message = f"{TABLE} e append-only - {operation} nao e permitido"
            op.execute(
                f"CREATE TRIGGER {trigger} BEFORE {operation} ON {TABLE} "
                f"BEGIN SELECT RAISE(ABORT, '{message}'); END"
            )
