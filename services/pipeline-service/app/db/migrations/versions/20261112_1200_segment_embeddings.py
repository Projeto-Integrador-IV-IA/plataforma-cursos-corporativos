"""Habilita pgvector e cria o armazenamento de embeddings de trecho (card #158).

Revision ID: 20261112_1200
Revises: 20261101_1300

RNF28 consolidado (ADR-0007): armazenamento vinculado ao trecho citavel
(``source_segments``), via a extensao ``vector`` do Postgres, sem banco
vetorial dedicado. Chave composta ``(segment_id, model)`` - mais de um modelo
pode coexistir sem apagar o anterior (append-only, RNF09, mesmos gatilhos de
``artifact_versions``).

No SQLite (testes), ``vector`` nao existe: a coluna fica como JSON (lista de
floats) via ``VECTOR_TYPE`` (``app/models/_types.py``), e o indice de
similaridade abaixo e criado so no Postgres - a busca por similaridade em si
(card #159) e feita em Python, no repositorio, portavel entre os dois
dialetos (ver justificativa no repositorio).
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

from app.models._types import UUID_TYPE, VECTOR_TYPE

revision: str = "20261112_1200"
down_revision: str | None = "20261101_1300"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

TABLE = "segment_embeddings"
FUNCTION = "segment_embeddings_refuse_change"
UPDATE_TRIGGER = "trg_segment_embeddings_refuse_update"
DELETE_TRIGGER = "trg_segment_embeddings_refuse_delete"
TRUNCATE_TRIGGER = "trg_segment_embeddings_refuse_truncate"
VECTOR_INDEX = "ix_segment_embeddings_vector_cosine"


def upgrade() -> None:
    dialect = op.get_bind().dialect.name
    if dialect == "postgresql":
        op.execute('CREATE EXTENSION IF NOT EXISTS "vector"')

    op.create_table(
        TABLE,
        sa.Column("segment_id", UUID_TYPE, primary_key=True),
        sa.Column("model", sa.Text, primary_key=True),
        sa.Column("vector", VECTOR_TYPE, nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.func.now(),
        ),
        sa.ForeignKeyConstraint(
            ["segment_id"],
            ["source_segments.id"],
            name="fk_segment_embeddings_segment_id_source_segments",
            ondelete="RESTRICT",
        ),
        sa.CheckConstraint("length(trim(model)) > 0", name="model_not_blank"),
    )

    if dialect == "postgresql":
        _create_postgresql_triggers()
        # hnsw: nao exige "lists" calibrado ao tamanho da tabela (diferente de
        # ivfflat) - melhor padrao para uma tabela que comeca vazia (RF29, MVP).
        op.execute(f"CREATE INDEX {VECTOR_INDEX} ON {TABLE} USING hnsw (vector vector_cosine_ops)")
    elif dialect == "sqlite":
        _create_sqlite_triggers()
    else:
        raise NotImplementedError(f"gatilho append-only nao implementado para {dialect}")


def downgrade() -> None:
    dialect = op.get_bind().dialect.name
    if dialect == "postgresql":
        op.execute(f"DROP INDEX {VECTOR_INDEX}")
        op.execute(f"DROP TRIGGER {TRUNCATE_TRIGGER} ON {TABLE}")
        op.execute(f"DROP TRIGGER {DELETE_TRIGGER} ON {TABLE}")
        op.execute(f"DROP TRIGGER {UPDATE_TRIGGER} ON {TABLE}")
        op.execute(f"DROP FUNCTION {FUNCTION}()")
    elif dialect == "sqlite":
        op.execute(f"DROP TRIGGER {DELETE_TRIGGER}")
        op.execute(f"DROP TRIGGER {UPDATE_TRIGGER}")
    else:
        raise NotImplementedError(f"gatilho append-only nao implementado para {dialect}")

    op.drop_table(TABLE)


def _create_postgresql_triggers() -> None:
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
