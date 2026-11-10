"""Edicao da saida da IA (RF14, Q1): vira versao nova, nunca sobrescreve.

A correcao humana e salva como versao vigente, ligada a versao de que partiu e a
versao da IA que originou a cadeia - o que permite comparar o que a IA gerou com
o que o humano revisou.
"""

from uuid import UUID, uuid4

import pytest
import sqlalchemy as sa
from fastapi.testclient import TestClient
from sqlalchemy.engine import Engine
from sqlalchemy.orm import Session

from app.domain.enums import ArtifactOrigin, ArtifactType
from app.models import Artifact, ArtifactVersion

from ._schema import (
    DEMAND_ID,
    USER_ID,
    assert_rejected,
    insert_client,
    insert_demand,
    insert_user,
)

IA_1 = {"tema": "Lideranca", "carga_horaria": None}
EDIT_A = {"tema": "Lideranca para gestores", "carga_horaria": None}
EDIT_B = {"tema": "Lideranca para gestores", "carga_horaria": 40}
IA_2 = {"tema": "Lideranca e feedback", "carga_horaria": 30}
EDIT_C = {"tema": "Lideranca e feedback", "carga_horaria": 32}


@pytest.fixture
def artifact_id(engine: Engine) -> UUID:
    """Artefato com a versao 1, gerada pela IA."""

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
                content=IA_1,
                origin=ArtifactOrigin.IA.value,
                ai_metadata={"model": "teste"},
            )
        )
        session.commit()
        return artifact.id


def _edit(api: TestClient, artifact_id: UUID, content: dict, base: int, author=USER_ID):
    return api.post(
        f"/api/v1/artifacts/{artifact_id}/versions",
        headers={"X-User-ID": str(author)},
        json={"structured_content": content, "base_number": base},
    )


def _rows(engine: Engine, artifact_id: UUID) -> list[tuple]:
    with Session(engine) as session:
        versions = session.scalars(
            sa.select(ArtifactVersion)
            .where(ArtifactVersion.artifact_id == artifact_id)
            .order_by(ArtifactVersion.number)
        ).all()
        return [
            (
                v.id,
                v.number,
                v.previous_number,
                v.ai_origin_number,
                v.origin,
                v.content,
                v.created_at,
            )
            for v in versions
        ]


def test_edit_creates_a_new_current_version_pointing_to_the_ai_version(
    api: TestClient, engine: Engine, artifact_id: UUID
) -> None:
    before = _rows(engine, artifact_id)

    response = _edit(api, artifact_id, EDIT_A, base=1)

    assert response.status_code == 201, response.text
    body = response.json()
    assert body["number"] == 2
    assert body["previous_number"] == 1
    assert body["ai_origin_number"] == 1
    assert body["origin"] == ArtifactOrigin.HUMANO.value
    assert body["author_id"] == str(UUID(USER_ID))
    assert body["structured_content"] == EDIT_A
    assert body["restored_from_number"] is None
    assert body["raw_output"] is None
    # A versao da IA continua exatamente como estava.
    assert _rows(engine, artifact_id)[:1] == before


def test_chained_edits_all_point_to_the_ai_version_that_started_the_chain(
    api: TestClient, engine: Engine, artifact_id: UUID
) -> None:
    assert _edit(api, artifact_id, EDIT_A, base=1).status_code == 201
    assert _edit(api, artifact_id, EDIT_B, base=2).status_code == 201

    rows = _rows(engine, artifact_id)

    assert [(r[1], r[2], r[3]) for r in rows] == [(1, None, None), (2, 1, 1), (3, 2, 1)]
    assert [r[5] for r in rows] == [IA_1, EDIT_A, EDIT_B]


def test_edit_after_a_newer_ai_version_points_to_that_newer_one(
    api: TestClient, engine: Engine, artifact_id: UUID
) -> None:
    assert _edit(api, artifact_id, EDIT_A, base=1).status_code == 201
    with Session(engine) as session:
        session.add(
            ArtifactVersion(
                artifact_id=artifact_id,
                number=3,
                previous_number=2,
                raw_content="nova resposta",
                content=IA_2,
                origin=ArtifactOrigin.IA.value,
            )
        )
        session.commit()

    response = _edit(api, artifact_id, EDIT_C, base=3)

    assert response.status_code == 201
    assert response.json()["ai_origin_number"] == 3
    assert response.json()["previous_number"] == 3


def test_restoring_keeps_the_ai_origin_of_the_restored_version(
    api: TestClient, engine: Engine, artifact_id: UUID
) -> None:
    assert _edit(api, artifact_id, EDIT_A, base=1).status_code == 201

    from_ai = api.post(
        f"/api/v1/artifacts/{artifact_id}/versions/1/restore",
        headers={"X-User-ID": USER_ID},
    )
    from_human = api.post(
        f"/api/v1/artifacts/{artifact_id}/versions/2/restore",
        headers={"X-User-ID": USER_ID},
    )

    assert from_ai.status_code == 201
    assert from_ai.json()["ai_origin_number"] == 1
    assert from_human.status_code == 201
    assert from_human.json()["ai_origin_number"] == 1


def test_stale_edit_is_refused_and_nothing_is_lost(
    api: TestClient, engine: Engine, artifact_id: UUID
) -> None:
    assert _edit(api, artifact_id, EDIT_A, base=1).status_code == 201

    response = _edit(api, artifact_id, EDIT_B, base=1)

    assert response.status_code == 409
    assert response.json()["error"]["code"] == "ARTIFACT_VERSION_NOT_CURRENT"
    assert [r[1] for r in _rows(engine, artifact_id)] == [1, 2]


def test_edit_with_unchanged_content_is_refused(
    api: TestClient, engine: Engine, artifact_id: UUID
) -> None:
    response = _edit(api, artifact_id, IA_1, base=1)

    assert response.status_code == 409
    assert response.json()["error"]["code"] == "ARTIFACT_CONTENT_UNCHANGED"
    assert len(_rows(engine, artifact_id)) == 1


def test_unknown_artifact_version_and_author_are_not_found(
    api: TestClient, engine: Engine, artifact_id: UUID
) -> None:
    missing_artifact = _edit(api, uuid4(), EDIT_A, base=1)
    missing_version = _edit(api, artifact_id, EDIT_A, base=9)
    missing_author = _edit(api, artifact_id, EDIT_A, base=1, author=uuid4())

    assert missing_artifact.json()["error"]["code"] == "ARTIFACT_NOT_FOUND"
    assert missing_version.json()["error"]["code"] == "ARTIFACT_VERSION_NOT_FOUND"
    assert missing_author.json()["error"]["code"] == "USER_NOT_FOUND"
    assert {r.status_code for r in (missing_artifact, missing_version, missing_author)} == {404}
    assert len(_rows(engine, artifact_id)) == 1


@pytest.mark.parametrize(
    "body",
    [
        {"structured_content": {}, "base_number": 1},
        {"structured_content": {"tema": "x"}, "base_number": 0},
        {"structured_content": {"tema": "x"}},
        {"base_number": 1},
        {"structured_content": {"tema": "x"}, "base_number": 1, "origin": "IA"},
    ],
)
def test_invalid_bodies_are_rejected(
    api: TestClient, engine: Engine, artifact_id: UUID, body: dict
) -> None:
    response = api.post(
        f"/api/v1/artifacts/{artifact_id}/versions",
        headers={"X-User-ID": USER_ID},
        json=body,
    )

    assert response.status_code == 422
    assert len(_rows(engine, artifact_id)) == 1


def test_author_header_is_required(api: TestClient, artifact_id: UUID) -> None:
    response = api.post(
        f"/api/v1/artifacts/{artifact_id}/versions",
        json={"structured_content": {"tema": "x"}, "base_number": 1},
    )

    assert response.status_code == 422


def test_edit_is_documented_in_swagger(api: TestClient) -> None:
    operation = api.app.openapi()["paths"]["/api/v1/artifacts/{artifact_id}/versions"]["post"]

    assert operation["summary"]
    assert "nunca sobrescreve" in operation["description"]
    assert {"201", "404", "409", "422"} <= set(operation["responses"])


@pytest.mark.parametrize(
    ("number", "previous", "origin", "ai_origin"),
    [
        (2, 1, "HUMANO", 2),  # aponta para a propria versao
        (2, 1, "HUMANO", 5),  # aponta para uma posterior
        (2, 1, "HUMANO", 0),  # aponta para uma que nao existe
        (2, 1, "IA", 1),  # versao da IA nao tem origem de IA
    ],
)
def test_database_refuses_an_inconsistent_ai_origin(
    engine: Engine, artifact_id: UUID, number: int, previous: int, origin: str, ai_origin: int
) -> None:
    with engine.connect() as connection:
        assert_rejected(
            connection,
            """
            INSERT INTO artifact_versions
                (id, artifact_id, number, previous_number, content, origin, raw_content,
                 author_id, ai_origin_number)
            VALUES (:id, :artifact_id, :number, :previous, '{}', :origin, 'bruto',
                    :author_id, :ai_origin)
            """,
            {
                "id": uuid4().hex,
                "artifact_id": artifact_id.hex,
                "number": number,
                "previous": previous,
                "origin": origin,
                "author_id": USER_ID,
                "ai_origin": ai_origin,
            },
        )

    assert len(_rows(engine, artifact_id)) == 1
