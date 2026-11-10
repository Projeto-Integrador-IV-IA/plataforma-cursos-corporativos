"""RF19.1: cada edicao salva e uma nova versao humana com origem rastreavel."""

from uuid import UUID, uuid4

import pytest
from alembic import command
from alembic.config import Config
from fastapi.testclient import TestClient
from sqlalchemy.engine import Engine
from sqlalchemy.orm import Session

from app.repositories.artifact_version_repository import ArtifactVersionRepository

from ._schema import USER_ID, assert_rejected
from .test_artifact_versions import V1, _append_human_versions, _rows
from .test_artifact_versions import artifact_id as artifact_id

EDIT = {"tema": "Lideranca revisada", "carga_horaria": 40}


def _save(api: TestClient, artifact_id: UUID, base: int = 1):
    return api.post(
        f"/api/v1/artifacts/{artifact_id}/versions",
        headers={"X-User-ID": USER_ID},
        json={"base_version_number": base, "structured_content": EDIT},
    )


def test_each_save_creates_a_human_version_without_changing_the_ai(
    api: TestClient, engine: Engine, artifact_id: UUID
) -> None:
    before = _rows(engine, artifact_id)
    first = _save(api, artifact_id)
    assert first.status_code == 201
    body = first.json()
    assert body["number"] == 2
    assert body["previous_number"] == body["ai_origin_number"] == 1
    assert body["origin"] == "HUMANO"
    assert body["author_id"] == str(UUID(USER_ID))
    assert body["created_at"]
    assert body["structured_content"] == EDIT
    assert body["raw_output"] is None
    assert body["ai_metadata"] is None
    assert body["restored_from_number"] is None

    second = _save(api, artifact_id, 2)
    assert second.status_code == 201
    assert second.json()["number"] == 3
    assert second.json()["previous_number"] == 2
    assert second.json()["ai_origin_number"] == 1
    assert _rows(engine, artifact_id)[:1] == before
    listed = api.get(f"/api/v1/artifacts/{artifact_id}/versions").json()
    assert [v["structured_content"] for v in listed] == [V1, EDIT, EDIT]


def test_stale_save_is_a_conflict_and_does_not_create_a_version(
    api: TestClient, engine: Engine, artifact_id: UUID
) -> None:
    assert _save(api, artifact_id).status_code == 201
    before = _rows(engine, artifact_id)
    response = _save(api, artifact_id)
    assert response.status_code == 409
    assert response.json()["error"]["code"] == "ARTIFACT_VERSION_STALE"
    assert _rows(engine, artifact_id) == before


def test_origin_follows_restoration_instead_of_the_latest_ai_version(
    api: TestClient, engine: Engine, artifact_id: UUID
) -> None:
    with Session(engine) as session:
        repo = ArtifactVersionRepository(session)
        repo.get_artifact_for_update(artifact_id)
        repo.append(artifact_id, content={"tema": "Outra IA"}, origin="IA", raw_content="novo")
        session.commit()
    restored = api.post(
        f"/api/v1/artifacts/{artifact_id}/versions/1/restore", headers={"X-User-ID": USER_ID}
    )
    assert restored.status_code == 201
    response = _save(api, artifact_id, 3)
    assert response.status_code == 201
    assert response.json()["ai_origin_number"] == 1
    assert response.json()["previous_number"] == 3


@pytest.mark.parametrize(
    ("body", "headers", "status", "code"),
    [
        (
            {"base_version_number": 99, "structured_content": EDIT},
            {"X-User-ID": USER_ID},
            404,
            "ARTIFACT_VERSION_NOT_FOUND",
        ),
        (
            {"base_version_number": 1, "structured_content": EDIT},
            {"X-User-ID": str(uuid4())},
            404,
            "USER_NOT_FOUND",
        ),
        ({"base_version_number": 0, "structured_content": EDIT}, {"X-User-ID": USER_ID}, 422, None),
        ({"base_version_number": 1, "structured_content": {}}, {"X-User-ID": USER_ID}, 422, None),
        ({"base_version_number": 1, "structured_content": []}, {"X-User-ID": USER_ID}, 422, None),
        ({"structured_content": EDIT}, {"X-User-ID": USER_ID}, 422, None),
        (
            {"base_version_number": 1, "structured_content": EDIT, "origin": "IA"},
            {"X-User-ID": USER_ID},
            422,
            None,
        ),
        ({"base_version_number": 1, "structured_content": EDIT}, {}, 422, None),
    ],
)
def test_invalid_edit_does_not_change_history(
    api: TestClient, engine: Engine, artifact_id: UUID, body, headers, status, code
) -> None:
    before = _rows(engine, artifact_id)
    response = api.post(f"/api/v1/artifacts/{artifact_id}/versions", json=body, headers=headers)
    assert response.status_code == status
    if code:
        assert response.json()["error"]["code"] == code
    assert _rows(engine, artifact_id) == before


def test_unknown_artifact_is_not_found(api: TestClient) -> None:
    assert _save(api, uuid4()).status_code == 404


def test_human_only_artifact_cannot_claim_an_ai_origin(
    api: TestClient, engine: Engine, artifact_id: UUID
) -> None:
    # Um segundo artefato sem IA nao pode herdar a origem do primeiro.
    from app.models import Artifact

    with Session(engine) as session:
        original = session.get(Artifact, artifact_id)
        human = Artifact(demand_id=original.demand_id, type=original.type)
        session.add(human)
        session.flush()
        ArtifactVersionRepository(session).append(
            human.id, content=EDIT, origin="HUMANO", author_id=UUID(USER_ID)
        )
        session.commit()
        human_id = human.id
    response = _save(api, human_id)
    assert response.status_code == 409
    assert response.json()["error"]["code"] == "ARTIFACT_AI_ORIGIN_NOT_FOUND"


def test_migration_preserves_existing_versions_and_append_only_triggers(
    engine: Engine, artifact_id: UUID
) -> None:
    _append_human_versions(engine, artifact_id, [EDIT])
    before = _rows(engine, artifact_id)
    config = Config("alembic.ini")
    command.downgrade(config, "20261101_1300")
    command.upgrade(config, "head")
    assert _rows(engine, artifact_id) == before
    with engine.connect() as connection:
        assert_rejected(connection, "UPDATE artifact_versions SET content = '{}'", {})
        assert_rejected(connection, "DELETE FROM artifact_versions", {})
        assert_rejected(
            connection,
            """INSERT INTO artifact_versions
            (id, artifact_id, number, previous_number, ai_origin_number, content, origin, author_id)
            VALUES (:id, :artifact, 3, 2, 3, '{}', 'HUMANO', :author)""",
            {"id": uuid4().hex, "artifact": artifact_id.hex, "author": USER_ID},
        )


def test_edit_endpoint_is_documented(api: TestClient) -> None:
    operation = api.app.openapi()["paths"]["/api/v1/artifacts/{artifact_id}/versions"]["post"]
    assert {"201", "404", "409", "422"} <= set(operation["responses"])
    assert "base_version_number" in operation["description"]
