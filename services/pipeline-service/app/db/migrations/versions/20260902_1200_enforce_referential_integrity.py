"""Cria o schema relacional com integridade referencial estrita (RNF14).

Revision ID: 20260902_1200
Revises:

Rastreabilidade: RNF14 - Documento Consolidado de Requisitos v1.0.
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "20260902_1200"
down_revision: str | None = None
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

UUID_TYPE = sa.Uuid().with_variant(postgresql.UUID(as_uuid=True), "postgresql")
JSON_TYPE = sa.JSON().with_variant(postgresql.JSONB(), "postgresql")

PIPELINE_STAGES = (
    "CAPTACAO",
    "ESTRUTURACAO",
    "PRODUTO",
    "PROPOSTA",
    "ACOMPANHAMENTO",
)
DEMAND_STATUSES = ("ABERTA", "GANHA", "PERDIDA", "CANCELADA")
RAW_INPUT_SOURCES = ("EMAIL", "TRANSCRICAO", "MENSAGENS", "ANOTACAO", "OUTRO")
ARTIFACT_TYPES = ("DEMANDA_BRUTA", "REQUISITOS_EXTRAIDOS", "EMENTA", "PROPOSTA", "OUTRO")
ARTIFACT_ORIGINS = ("IA", "HUMANO")


def quoted_values(values: tuple[str, ...]) -> str:
    """Converte um vocabulario fechado para uma lista SQL literal."""

    return ", ".join(f"'{value}'" for value in values)


def upgrade() -> None:
    """Cria entidades, chaves estrangeiras e restricoes do dominio."""

    op.create_table(
        "users",
        sa.Column(
            "id",
            UUID_TYPE,
            server_default=sa.text("gen_random_uuid()"),
            nullable=False,
        ),
        sa.Column("name", sa.Text(), nullable=False),
        sa.Column("email", sa.Text(), nullable=False),
        sa.Column("password_hash", sa.Text(), nullable=False),
        sa.Column("role", sa.Text(), server_default=sa.text("'OPERADOR'"), nullable=False),
        sa.Column("active", sa.Boolean(), server_default=sa.true(), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.CheckConstraint("role IN ('OPERADOR')", name="ck_users_role"),
        sa.PrimaryKeyConstraint("id", name="pk_users"),
        sa.UniqueConstraint("email", name="uq_users_email"),
    )

    op.create_table(
        "clients",
        sa.Column(
            "id",
            UUID_TYPE,
            server_default=sa.text("gen_random_uuid()"),
            nullable=False,
        ),
        sa.Column("name", sa.Text(), nullable=False),
        sa.Column("cnpj", sa.Text(), nullable=True),
        sa.Column("segment", sa.Text(), nullable=True),
        sa.Column("contact_name", sa.Text(), nullable=True),
        sa.Column("contact_email", sa.Text(), nullable=True),
        sa.Column("contact_phone", sa.Text(), nullable=True),
        sa.Column("notes", sa.Text(), nullable=True),
        sa.Column("active", sa.Boolean(), server_default=sa.true(), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.PrimaryKeyConstraint("id", name="pk_clients"),
        sa.UniqueConstraint("cnpj", name="uq_clients_cnpj"),
    )

    op.create_table(
        "demands",
        sa.Column(
            "id",
            UUID_TYPE,
            server_default=sa.text("gen_random_uuid()"),
            nullable=False,
        ),
        sa.Column("client_id", UUID_TYPE, nullable=False),
        sa.Column("title", sa.Text(), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column(
            "current_stage",
            sa.Text(),
            server_default=sa.text("'CAPTACAO'"),
            nullable=False,
        ),
        sa.Column("status", sa.Text(), server_default=sa.text("'ABERTA'"), nullable=False),
        sa.Column("owner_id", UUID_TYPE, nullable=True),
        sa.Column("active", sa.Boolean(), server_default=sa.true(), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.CheckConstraint(
            f"current_stage IN ({quoted_values(PIPELINE_STAGES)})",
            name="ck_demands_current_stage",
        ),
        sa.CheckConstraint(
            f"status IN ({quoted_values(DEMAND_STATUSES)})",
            name="ck_demands_status",
        ),
        sa.ForeignKeyConstraint(
            ["client_id"],
            ["clients.id"],
            name="fk_demands_client_id_clients",
            ondelete="RESTRICT",
        ),
        sa.ForeignKeyConstraint(
            ["owner_id"],
            ["users.id"],
            name="fk_demands_owner_id_users",
            ondelete="RESTRICT",
        ),
        sa.PrimaryKeyConstraint("id", name="pk_demands"),
    )

    op.create_table(
        "raw_inputs",
        sa.Column(
            "id",
            UUID_TYPE,
            server_default=sa.text("gen_random_uuid()"),
            nullable=False,
        ),
        sa.Column("demand_id", UUID_TYPE, nullable=False),
        sa.Column("original_content", sa.Text(), nullable=False),
        sa.Column("normalized_content", sa.Text(), nullable=True),
        sa.Column("source", sa.Text(), nullable=False),
        sa.Column("truncated", sa.Boolean(), server_default=sa.false(), nullable=False),
        sa.Column("author_id", UUID_TYPE, nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.CheckConstraint(
            f"source IN ({quoted_values(RAW_INPUT_SOURCES)})",
            name="ck_raw_inputs_source",
        ),
        sa.ForeignKeyConstraint(
            ["author_id"],
            ["users.id"],
            name="fk_raw_inputs_author_id_users",
            ondelete="RESTRICT",
        ),
        sa.ForeignKeyConstraint(
            ["demand_id"],
            ["demands.id"],
            name="fk_raw_inputs_demand_id_demands",
            ondelete="RESTRICT",
        ),
        sa.PrimaryKeyConstraint("id", name="pk_raw_inputs"),
        sa.UniqueConstraint("id", "demand_id", name="uq_raw_inputs_id_demand_id"),
    )

    op.create_table(
        "stage_transitions",
        sa.Column(
            "id",
            UUID_TYPE,
            server_default=sa.text("gen_random_uuid()"),
            nullable=False,
        ),
        sa.Column("demand_id", UUID_TYPE, nullable=False),
        sa.Column("from_stage", sa.Text(), nullable=True),
        sa.Column("to_stage", sa.Text(), nullable=False),
        sa.Column("reason", sa.Text(), nullable=True),
        sa.Column("author_id", UUID_TYPE, nullable=False),
        sa.Column(
            "occurred_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.CheckConstraint(
            f"from_stage IS NULL OR from_stage IN ({quoted_values(PIPELINE_STAGES)})",
            name="ck_stage_transitions_from_stage",
        ),
        sa.CheckConstraint(
            f"to_stage IN ({quoted_values(PIPELINE_STAGES)})",
            name="ck_stage_transitions_to_stage",
        ),
        sa.CheckConstraint(
            "from_stage IS NULL OR from_stage <> to_stage",
            name="ck_stage_transitions_distinct_stages",
        ),
        sa.ForeignKeyConstraint(
            ["author_id"],
            ["users.id"],
            name="fk_stage_transitions_author_id_users",
            ondelete="RESTRICT",
        ),
        sa.ForeignKeyConstraint(
            ["demand_id"],
            ["demands.id"],
            name="fk_stage_transitions_demand_id_demands",
            ondelete="RESTRICT",
        ),
        sa.PrimaryKeyConstraint("id", name="pk_stage_transitions"),
    )

    op.create_table(
        "artifacts",
        sa.Column(
            "id",
            UUID_TYPE,
            server_default=sa.text("gen_random_uuid()"),
            nullable=False,
        ),
        sa.Column("demand_id", UUID_TYPE, nullable=False),
        sa.Column("type", sa.Text(), nullable=False),
        sa.Column("title", sa.Text(), nullable=True),
        sa.Column("raw_input_id", UUID_TYPE, nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.CheckConstraint(
            f"type IN ({quoted_values(ARTIFACT_TYPES)})",
            name="ck_artifacts_type",
        ),
        sa.ForeignKeyConstraint(
            ["demand_id"],
            ["demands.id"],
            name="fk_artifacts_demand_id_demands",
            ondelete="RESTRICT",
        ),
        sa.ForeignKeyConstraint(
            ["raw_input_id", "demand_id"],
            ["raw_inputs.id", "raw_inputs.demand_id"],
            name="fk_artifacts_raw_input_demand",
            ondelete="RESTRICT",
        ),
        sa.PrimaryKeyConstraint("id", name="pk_artifacts"),
    )

    op.create_table(
        "artifact_versions",
        sa.Column(
            "id",
            UUID_TYPE,
            server_default=sa.text("gen_random_uuid()"),
            nullable=False,
        ),
        sa.Column("artifact_id", UUID_TYPE, nullable=False),
        sa.Column("number", sa.Integer(), nullable=False),
        sa.Column("content", JSON_TYPE, nullable=False),
        sa.Column("origin", sa.Text(), nullable=False),
        sa.Column("ai_metadata", JSON_TYPE, nullable=True),
        sa.Column("author_id", UUID_TYPE, nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.CheckConstraint("number > 0", name="ck_artifact_versions_number_positive"),
        sa.CheckConstraint(
            f"origin IN ({quoted_values(ARTIFACT_ORIGINS)})",
            name="ck_artifact_versions_origin",
        ),
        sa.ForeignKeyConstraint(
            ["artifact_id"],
            ["artifacts.id"],
            name="fk_artifact_versions_artifact_id_artifacts",
            ondelete="RESTRICT",
        ),
        sa.ForeignKeyConstraint(
            ["author_id"],
            ["users.id"],
            name="fk_artifact_versions_author_id_users",
            ondelete="RESTRICT",
        ),
        sa.PrimaryKeyConstraint("id", name="pk_artifact_versions"),
        sa.UniqueConstraint("artifact_id", "number", name="uq_artifact_versions_number"),
    )

    op.create_index(
        "ix_demands_client_status_created_at",
        "demands",
        ["client_id", "status", "created_at"],
    )
    op.create_index("ix_demands_current_stage", "demands", ["current_stage"])
    op.create_index(
        "ix_raw_inputs_demand_created_at",
        "raw_inputs",
        ["demand_id", "created_at"],
    )
    op.create_index(
        "ix_stage_transitions_demand_occurred_at",
        "stage_transitions",
        ["demand_id", "occurred_at"],
    )
    op.create_index("ix_artifacts_demand_id", "artifacts", ["demand_id"])


def downgrade() -> None:
    """Remove o schema na ordem inversa das dependencias."""

    op.drop_table("artifact_versions")
    op.drop_table("artifacts")
    op.drop_table("stage_transitions")
    op.drop_table("raw_inputs")
    op.drop_table("demands")
    op.drop_table("clients")
    op.drop_table("users")
