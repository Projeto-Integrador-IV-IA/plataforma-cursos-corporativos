"""Versoes de artefato (RF08): nunca sobrescritas, encadeadas e listaveis.

Cada alteracao cria um registro novo. O ORM e o banco recusam alterar ou apagar
uma versao ja gravada, e cada versao aponta para a sua antecessora.
"""

from uuid import UUID, uuid4

import pytest
import sqlalchemy as sa
from fastapi.testclient import TestClient
from sqlalchemy.engine import Engine
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.domain.enums import ArtifactOrigin, ArtifactType
from app.models import Artifact, ArtifactVersion
from app.models._append_only import AppendOnlyViolationError
from app.repositories.artifact_version_repository import ArtifactVersionRepository

from ._schema import (
    DEMAND_ID,
    USER_ID,
    assert_rejected,
    insert_client,
    insert_demand,
    insert_user,
)

V1 = {"tema": "Lideranca"}
V2 = {"tema": "Lideranca para gestores"}
V3 = {"tema": "Lideranca para gestores", "carga_horaria": 40}


@pytest.fixture
def artifact_id(engine: Engine) -> UUID:
    """Artefato com a versao 1, gerada pela IA, na demanda de teste."""

    with engine.connect() as connection:
        insert_user(connection)
        insert_client(connection)
        insert_demand(connection)
    with Session(engine) as session:
        artifact = Artifact(
            demand_id=UUID(DEMAND_ID), type=ArtifactType.REQUISITOS_EXTRAIDOS.value, title="Ementa"
        )
        session.add(artifact)
        session.flush()
        session.add(
            ArtifactVersion(
                artifact_id=artifact.id,
                number=1,
                raw_content="resposta bruta",
                content=V1,
                origin=ArtifactOrigin.IA.value,
            )
        )
        session.commit()
        return artifact.id


def _append_human_versions(engine: Engine, artifact_id: UUID, contents: list[dict]) -> None:
    with Session(engine) as session:
        repository = ArtifactVersionRepository(session)
        repository.get_artifact_for_update(artifact_id)
        for content in contents:
            repository.append(
                artifact_id,
                content=content,
                origin=ArtifactOrigin.HUMANO.value,
                author_id=UUID(USER_ID),
            )
        session.commit()


def _rows(engine: Engine, artifact_id: UUID) -> list[tuple]:
    with Session(engine) as session:
        versions = session.scalars(
            sa.select(ArtifactVersion)
            .where(ArtifactVersion.artifact_id == artifact_id)
            .order_by(ArtifactVersion.number)
        ).all()
        return [
            (v.id, v.number, v.previous_number, v.origin, v.content, v.raw_content, v.created_at)
            for v in versions
        ]


# --- escrita so por insercao ---------------------------------------------------


def test_append_numbers_each_version_and_links_it_to_the_previous(
    engine: Engine, artifact_id: UUID
) -> None:
    _append_human_versions(engine, artifact_id, [V2, V3])

    rows = _rows(engine, artifact_id)

    assert [(r[1], r[2]) for r in rows] == [(1, None), (2, 1), (3, 2)]
    assert [r[4] for r in rows] == [V1, V2, V3]


def test_a_new_version_never_overwrites_the_previous_one(engine: Engine, artifact_id: UUID) -> None:
    before = _rows(engine, artifact_id)

    _append_human_versions(engine, artifact_id, [V2])

    after = _rows(engine, artifact_id)
    assert after[:1] == before
    assert len(after) == 2


def test_repository_has_no_update_or_delete_path() -> None:
    public = {name for name in dir(ArtifactVersionRepository) if not name.startswith("_")}

    assert "append" in public
    assert not {n for n in public if n.startswith(("update", "delete", "remove", "edit", "save"))}


def test_orm_refuses_to_change_or_delete_a_version(engine: Engine, artifact_id: UUID) -> None:
    with Session(engine) as session:
        version = session.scalars(sa.select(ArtifactVersion)).one()

        version.content = {"tema": "adulterado"}
        with pytest.raises(AppendOnlyViolationError):
            session.flush()
        session.rollback()

        session.delete(version)
        with pytest.raises(AppendOnlyViolationError):
            session.flush()
        session.rollback()

    assert [r[4] for r in _rows(engine, artifact_id)] == [V1]


def test_database_refuses_update_and_delete_of_a_version(engine: Engine, artifact_id: UUID) -> None:
    with engine.connect() as connection:
        assert_rejected(connection, "UPDATE artifact_versions SET content = '{}'", {})
        assert_rejected(connection, "DELETE FROM artifact_versions", {})

    with Session(engine) as session:
        with pytest.raises(IntegrityError):
            session.execute(sa.update(ArtifactVersion).values(origin="HUMANO"))
        session.rollback()
        with pytest.raises(IntegrityError):
            session.execute(sa.delete(ArtifactVersion))
        session.rollback()

    assert [r[4] for r in _rows(engine, artifact_id)] == [V1]


def test_database_accepts_the_next_version_with_its_predecessor(
    engine: Engine, artifact_id: UUID
) -> None:
    with engine.connect() as connection:
        connection.execute(
            sa.text(
                """
                INSERT INTO artifact_versions
                    (id, artifact_id, number, previous_number, content, origin, author_id)
                VALUES (:id, :artifact_id, 2, 1, '{}', 'HUMANO', :author_id)
                """
            ),
            {"id": uuid4().hex, "artifact_id": artifact_id.hex, "author_id": USER_ID},
        )
        connection.commit()

    assert len(_rows(engine, artifact_id)) == 2


@pytest.mark.parametrize(("number", "previous"), [(2, None), (3, 1), (5, 4)])
def test_database_refuses_a_version_not_linked_to_its_immediate_predecessor(
    engine: Engine, artifact_id: UUID, number: int, previous: int | None
) -> None:
    """Sem antecessora, com a errada, ou com uma que nao existe."""

    with engine.connect() as connection:
        assert_rejected(
            connection,
            """
            INSERT INTO artifact_versions
                (id, artifact_id, number, previous_number, content, origin, author_id)
            VALUES (:id, :artifact_id, :number, :previous, '{}', 'HUMANO', :author_id)
            """,
            {
                "id": uuid4().hex,
                "artifact_id": artifact_id.hex,
                "number": number,
                "previous": previous,
                "author_id": USER_ID,
            },
        )

    assert len(_rows(engine, artifact_id)) == 1


# --- listagem ------------------------------------------------------------------


def test_list_returns_every_version_ordered_with_its_lineage(
    api: TestClient, engine: Engine, artifact_id: UUID
) -> None:
    _append_human_versions(engine, artifact_id, [V2, V3])

    response = api.get(f"/api/v1/artifacts/{artifact_id}/versions")

    assert response.status_code == 200
    versions = response.json()
    assert [v["number"] for v in versions] == [1, 2, 3]
    assert [v["previous_number"] for v in versions] == [None, 1, 2]
    assert [v["structured_content"] for v in versions] == [V1, V2, V3]
    assert [v["origin"] for v in versions] == ["IA", "HUMANO", "HUMANO"]
    assert versions[0]["raw_output"] == "resposta bruta"
    assert versions[1]["raw_output"] is None
    assert versions[1]["author_id"] == str(UUID(USER_ID))


def test_list_of_an_unknown_artifact_is_not_found(api: TestClient) -> None:
    response = api.get(f"/api/v1/artifacts/{uuid4()}/versions")

    assert response.status_code == 404
    assert response.json()["error"]["code"] == "ARTIFACT_NOT_FOUND"


def test_list_rejects_an_invalid_identifier(api: TestClient) -> None:
    assert api.get("/api/v1/artifacts/nao-e-uuid/versions").status_code == 422


def test_version_listing_is_documented_in_swagger(api: TestClient) -> None:
    operation = api.app.openapi()["paths"]["/api/v1/artifacts/{artifact_id}/versions"]["get"]

    assert operation["summary"]
    assert "sobrescrita" in operation["description"]
    assert {"200", "404", "422"} <= set(operation["responses"])
    schema = operation["responses"]["200"]["content"]["application/json"]["schema"]
    assert schema["type"] == "array"
    assert schema["items"]["$ref"].endswith("/ArtifactVersionRead")
