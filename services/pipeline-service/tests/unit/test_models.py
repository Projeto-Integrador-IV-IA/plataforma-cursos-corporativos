"""Contrato RNF08 entre os modelos ORM e o dicionario de dados."""

import importlib

import sqlalchemy as sa
from sqlalchemy.orm import Session

import app.models  # noqa: F401 - popula Base.metadata
from app.db.base import Base
from app.domain.enums import (
    ArtifactOrigin,
    ArtifactType,
    DemandStatus,
    PipelineStage,
    RawInputSource,
    enum_values,
)
from app.models import (
    Artifact,
    ArtifactVersion,
    Client,
    Demand,
    RawInput,
    StageTransition,
    User,
)

EXPECTED_COLUMNS = {
    "users": {"id", "name", "email", "password_hash", "role", "active", "created_at"},
    "clients": {
        "id",
        "name",
        "cnpj",
        "segment",
        "contact_name",
        "contact_email",
        "contact_phone",
        "notes",
        "active",
        "created_at",
        "updated_at",
    },
    "demands": {
        "id",
        "client_id",
        "title",
        "description",
        "current_stage",
        "status",
        "owner_id",
        "active",
        "created_at",
        "updated_at",
    },
    "raw_inputs": {
        "id",
        "demand_id",
        "original_content",
        "normalized_content",
        "source",
        "truncated",
        "author_id",
        "created_at",
    },
    "stage_transitions": {
        "id",
        "demand_id",
        "from_stage",
        "to_stage",
        "reason",
        "author_id",
        "occurred_at",
    },
    "artifacts": {"id", "demand_id", "type", "title", "raw_input_id", "created_at"},
    "artifact_versions": {
        "id",
        "artifact_id",
        "number",
        "content",
        "origin",
        "ai_metadata",
        "author_id",
        "created_at",
    },
}


def test_all_domain_entities_and_fields_are_mapped() -> None:
    assert set(Base.metadata.tables) == set(EXPECTED_COLUMNS)

    for table_name, expected_columns in EXPECTED_COLUMNS.items():
        assert set(Base.metadata.tables[table_name].columns.keys()) == expected_columns


def test_required_domain_relationships_are_not_nullable() -> None:
    required_relationships = {
        ("demands", "client_id"),
        ("raw_inputs", "demand_id"),
        ("raw_inputs", "author_id"),
        ("stage_transitions", "demand_id"),
        ("stage_transitions", "author_id"),
        ("artifacts", "demand_id"),
        ("artifact_versions", "artifact_id"),
    }

    nullable_relationships = {
        (table_name, column_name)
        for table_name, column_name in required_relationships
        if Base.metadata.tables[table_name].c[column_name].nullable
    }

    assert nullable_relationships == set()


def test_foreign_keys_restrict_deletion_and_source_stays_in_same_demand() -> None:
    foreign_keys = {
        constraint.name: constraint
        for table in Base.metadata.tables.values()
        for constraint in table.constraints
        if isinstance(constraint, sa.ForeignKeyConstraint)
    }

    assert foreign_keys
    assert all(constraint.ondelete == "RESTRICT" for constraint in foreign_keys.values())

    source_constraint = foreign_keys["fk_artifacts_raw_input_demand"]
    assert [element.parent.name for element in source_constraint.elements] == [
        "raw_input_id",
        "demand_id",
    ]
    assert [element.target_fullname for element in source_constraint.elements] == [
        "raw_inputs.id",
        "raw_inputs.demand_id",
    ]


def test_all_relationship_mappers_can_be_configured() -> None:
    sa.orm.configure_mappers()

    assert {mapper.local_table.name for mapper in Base.registry.mappers} == set(EXPECTED_COLUMNS)


def test_closed_vocabularies_match_initial_migration() -> None:
    migration = importlib.import_module(
        "app.db.migrations.versions.20260902_1200_enforce_referential_integrity"
    )

    assert enum_values(PipelineStage) == migration.PIPELINE_STAGES
    assert enum_values(DemandStatus) == migration.DEMAND_STATUSES
    assert enum_values(RawInputSource) == migration.RAW_INPUT_SOURCES
    assert enum_values(ArtifactType) == migration.ARTIFACT_TYPES
    assert enum_values(ArtifactOrigin) == migration.ARTIFACT_ORIGINS


def test_complete_domain_chain_can_be_persisted_through_orm() -> None:
    engine = sa.create_engine("sqlite+pysqlite:///:memory:")

    @sa.event.listens_for(engine, "connect")
    def enable_foreign_keys(dbapi_connection: object, _connection_record: object) -> None:
        cursor = dbapi_connection.cursor()  # type: ignore[attr-defined]
        cursor.execute("PRAGMA foreign_keys=ON")
        cursor.close()

    Base.metadata.create_all(engine)

    user = User(name="Operador", email="operador@example.com", password_hash="hash")
    client = Client(name="Cliente")
    demand = Demand(client=client, owner=user, title="Demanda")
    raw_input = RawInput(
        demand=demand,
        author=user,
        original_content="Conteudo original",
        source="EMAIL",
    )
    transition = StageTransition(
        demand=demand,
        author=user,
        from_stage=None,
        to_stage="CAPTACAO",
    )
    artifact = Artifact(
        demand=demand,
        raw_input=raw_input,
        type="EMENTA",
        title="Ementa",
    )
    version = ArtifactVersion(
        artifact=artifact,
        number=1,
        content={"titulo": "Curso"},
        origin="HUMANO",
        author=user,
    )

    with Session(engine) as session:
        session.add_all([transition, version])
        session.commit()

        assert session.scalar(sa.select(sa.func.count(Client.id))) == 1
        assert session.scalar(sa.select(sa.func.count(Demand.id))) == 1
        assert session.scalar(sa.select(sa.func.count(RawInput.id))) == 1
        assert session.scalar(sa.select(sa.func.count(StageTransition.id))) == 1
        assert session.scalar(sa.select(sa.func.count(Artifact.id))) == 1
        assert session.scalar(sa.select(sa.func.count(ArtifactVersion.id))) == 1

    engine.dispose()
