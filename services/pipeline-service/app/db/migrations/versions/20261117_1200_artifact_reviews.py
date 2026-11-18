"""Registra a decisao de revisao humana sobre uma versao de artefato (RF19.2).

Revision ID: 20261117_1200
Revises: 20261109_1200

Cards #58 (estado da revisao no backend), #59 (autor/data/justificativa) e
#60 (nao revisar versao que ja deixou de ser a vigente): a validacao de #60
e aplicada no servico, nao aqui - o banco so garante que a versao referenciada
existe e pertence ao mesmo artefato (FK composta). Append-only pelo mesmo
padrao de ``stage_transitions``/``artifact_versions``/``segment_embeddings``:
gatilhos BEFORE UPDATE/DELETE/TRUNCATE recusam qualquer alteracao ou remocao.
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

from app.domain.enums import ArtifactReviewDecision, sql_enum_values
from app.models._types import UUID_TYPE

revision: str = "20261117_1200"
down_revision: str | None = "20261109_1200"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

TABLE = "artifact_reviews"
FUNCTION = "artifact_reviews_refuse_change"
UPDATE_TRIGGER = "trg_artifact_reviews_refuse_update"
DELETE_TRIGGER = "trg_artifact_reviews_refuse_delete"
TRUNCATE_TRIGGER = "trg_artifact_reviews_refuse_truncate"


def upgrade() -> None:
    op.create_table(
        TABLE,
        sa.Column(
            "id",
            UUID_TYPE,
            primary_key=True,
            server_default=sa.text("gen_random_uuid()"),
        ),
        sa.Column("artifact_id", UUID_TYPE, nullable=False),
        sa.Column("version_number", sa.Integer, nullable=False),
        sa.Column("decision", sa.Text, nullable=False),
        sa.Column("reason", sa.Text, nullable=True),
        sa.Column("author_id", UUID_TYPE, nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.func.now(),
        ),
        sa.ForeignKeyConstraint(
            ["artifact_id"],
            ["artifacts.id"],
            name="fk_artifact_reviews_artifact_id_artifacts",
            ondelete="RESTRICT",
        ),
        sa.ForeignKeyConstraint(
            ["artifact_id", "version_number"],
            ["artifact_versions.artifact_id", "artifact_versions.number"],
            name="fk_artifact_reviews_version",
            ondelete="RESTRICT",
        ),
        sa.ForeignKeyConstraint(
            ["author_id"],
            ["users.id"],
            name="fk_artifact_reviews_author_id_users",
            ondelete="RESTRICT",
        ),
        sa.CheckConstraint(
            f"decision IN ({sql_enum_values(ArtifactReviewDecision)})",
            name="decision",
        ),
        sa.CheckConstraint(
            f"decision = '{ArtifactReviewDecision.APROVADO.value}' "
            "OR (reason IS NOT NULL AND length(trim(reason)) > 0)",
            name="rejection_or_return_requires_reason",
        ),
        sa.CheckConstraint("version_number > 0", name="version_number_positive"),
    )
    op.create_index("ix_artifact_reviews_artifact_created_at", TABLE, ["artifact_id", "created_at"])
    op.create_index("ix_artifact_reviews_author_id", TABLE, ["author_id"])

    dialect = op.get_bind().dialect.name
    if dialect == "postgresql":
        _create_postgresql_triggers()
    elif dialect == "sqlite":
        _create_sqlite_triggers()
    else:
        raise NotImplementedError(f"gatilho append-only nao implementado para {dialect}")


def downgrade() -> None:
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
