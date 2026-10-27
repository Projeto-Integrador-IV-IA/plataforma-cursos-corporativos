"""Torna as versoes de artefato append-only tambem no banco (RNF09, RF08).

Revision ID: 20261022_1300
Revises: 20261022_1200

Versao de artefato nunca e sobrescrita: cada alteracao cria um registro novo. O
repositorio so insere e o modelo recusa alteracao, mas nada disso impede UPDATE
ou DELETE feito por fora do ORM. Aqui o proprio banco recusa, com gatilhos
BEFORE UPDATE e BEFORE DELETE em ``artifact_versions`` (e BEFORE TRUNCATE no
PostgreSQL). INSERT segue livre.

Limites conhecidos: quem e dono da tabela ou superusuario pode desativar o
gatilho; o papel de aplicacao deve ter apenas INSERT e SELECT. E, no SQLite, uma
migration futura que use ``batch_alter_table("artifact_versions")`` recria a
tabela e perde os gatilhos - precisa recria-los.
"""

from collections.abc import Sequence

from alembic import op

revision: str = "20261022_1300"
down_revision: str | None = "20261022_1200"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

TABLE = "artifact_versions"
FUNCTION = "artifact_versions_refuse_change"
UPDATE_TRIGGER = "trg_artifact_versions_refuse_update"
DELETE_TRIGGER = "trg_artifact_versions_refuse_delete"
TRUNCATE_TRIGGER = "trg_artifact_versions_refuse_truncate"


def upgrade() -> None:
    """Cria os gatilhos que recusam UPDATE e DELETE nas versoes."""

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
