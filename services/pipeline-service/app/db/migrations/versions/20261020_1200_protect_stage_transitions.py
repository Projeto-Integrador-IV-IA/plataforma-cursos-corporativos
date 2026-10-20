"""Torna a trilha de etapas append-only tambem no banco (RNF09, RF07).

Revision ID: 20261020_1200
Revises: 20260920_1200

O repositorio so insere e o modelo recusa alteracao, mas nada disso impede um
UPDATE ou DELETE feito por fora do ORM. Aqui o proprio banco recusa: gatilhos
BEFORE UPDATE e BEFORE DELETE na tabela ``stage_transitions`` (e BEFORE TRUNCATE
no PostgreSQL). INSERT segue livre.

Limites conhecidos: quem e dono da tabela ou superusuario pode desativar ou
remover o gatilho; para fechar isso, o papel de aplicacao deve ter apenas
INSERT e SELECT na tabela. E, no SQLite, uma migration futura que use
``batch_alter_table("stage_transitions")`` recria a tabela e perde os gatilhos -
precisa recria-los.
"""

from collections.abc import Sequence

from alembic import op

revision: str = "20261020_1200"
down_revision: str | None = "20260920_1200"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

TABLE = "stage_transitions"
FUNCTION = "stage_transitions_refuse_change"
UPDATE_TRIGGER = "trg_stage_transitions_refuse_update"
DELETE_TRIGGER = "trg_stage_transitions_refuse_delete"
TRUNCATE_TRIGGER = "trg_stage_transitions_refuse_truncate"


def upgrade() -> None:
    """Cria os gatilhos que recusam UPDATE e DELETE na trilha."""

    dialect = op.get_bind().dialect.name
    if dialect == "postgresql":
        _create_postgresql_triggers()
    elif dialect == "sqlite":
        _create_sqlite_triggers()
    else:
        raise NotImplementedError(f"gatilho append-only nao implementado para {dialect}")


def downgrade() -> None:
    """Remove somente os gatilhos desta revisao."""

    dialect = op.get_bind().dialect.name
    if dialect == "postgresql":
        op.execute(f"DROP TRIGGER {TRUNCATE_TRIGGER} ON {TABLE}")
        op.execute(f"DROP TRIGGER {DELETE_TRIGGER} ON {TABLE}")
        op.execute(f"DROP TRIGGER {UPDATE_TRIGGER} ON {TABLE}")
        op.execute(f"DROP FUNCTION {FUNCTION}()")
    elif dialect == "sqlite":
        op.execute(f"DROP TRIGGER {DELETE_TRIGGER}")
        op.execute(f"DROP TRIGGER {UPDATE_TRIGGER}")
    else:
        raise NotImplementedError(f"gatilho append-only nao implementado para {dialect}")


def _create_postgresql_triggers() -> None:
    # Sem ``%`` nem ``:`` no texto: o driver e o ``text()`` os interpretariam.
    op.execute(
        f"""
        CREATE FUNCTION {FUNCTION}() RETURNS trigger
        LANGUAGE plpgsql AS $$
        BEGIN
            RAISE EXCEPTION USING
                MESSAGE = '{TABLE} e append-only - ' || TG_OP || ' nao e permitido',
                ERRCODE = 'restrict_violation';
        END;
        $$
        """
    )
    op.execute(
        f"CREATE TRIGGER {UPDATE_TRIGGER} BEFORE UPDATE ON {TABLE} "
        f"FOR EACH ROW EXECUTE FUNCTION {FUNCTION}()"
    )
    op.execute(
        f"CREATE TRIGGER {DELETE_TRIGGER} BEFORE DELETE ON {TABLE} "
        f"FOR EACH ROW EXECUTE FUNCTION {FUNCTION}()"
    )
    # TRUNCATE nao dispara gatilho de linha; precisa do gatilho de comando.
    op.execute(
        f"CREATE TRIGGER {TRUNCATE_TRIGGER} BEFORE TRUNCATE ON {TABLE} "
        f"FOR EACH STATEMENT EXECUTE FUNCTION {FUNCTION}()"
    )


def _create_sqlite_triggers() -> None:
    for trigger, operation in ((UPDATE_TRIGGER, "UPDATE"), (DELETE_TRIGGER, "DELETE")):
        op.execute(
            f"CREATE TRIGGER {trigger} BEFORE {operation} ON {TABLE} "
            f"BEGIN SELECT RAISE(ABORT, '{TABLE} e append-only - {operation} nao e permitido'); END"
        )
