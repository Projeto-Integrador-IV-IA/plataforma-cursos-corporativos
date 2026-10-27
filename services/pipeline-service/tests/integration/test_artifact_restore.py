"""Restauracao de versao de artefato (RF08): cria versao nova, preserva o historico.

Restaurar nao desfaz. A versao escolhida volta a valer como uma versao nova, as
intermediarias seguem intactas e consultaveis, e a propria versao nova registra
qual voltou, quem restaurou e quando.
"""

from uuid import UUID, uuid4

import pytest
import sqlalchemy as sa
from fastapi.testclient import TestClient
from sqlalchemy.engine import Engine
from sqlalchemy.orm import Session

from app.domain.enums import ArtifactOrigin, ArtifactType
from app.models import Artifact, ArtifactVersion
from app.models.demand import Demand
from app.models.user import User

from ._schema import assert_rejected

V1 = {"tema": "Lideranca", "carga_horaria": None}
V2 = {"tema": "Lideranca para gestores", "carga_horaria": 40}


def _create_user(engine: Engine, name: str = "Operador") -> UUID:
    with Session(engine) as session:
        user = User(name=name, email=f"{uuid4().hex}@example.com", password_hash="hash")
        session.add(user)
        session.commit()
        return user.id


def _create_artifact(engine: Engine, client_id: UUID, editor_id: UUID) -> tuple[UUID, UUID]:
    """Demanda com um artefato de duas versoes: 1 da IA e 2 editada por uma pessoa."""

    with Session(engine) as session:
        demand = Demand(client_id=client_id, title="Demanda")
        session.add(demand)
        session.flush()
        artifact = Artifact(
            demand_id=demand.id, type=ArtifactType.REQUISITOS_EXTRAIDOS.value, title="Ementa"
        )
        session.add(artifact)
        session.flush()
        session.add_all(
            [
                ArtifactVersion(
                    artifact_id=artifact.id,
                    number=1,
                    raw_content="resposta bruta do modelo",
                    content=V1,
                    origin=ArtifactOrigin.IA.value,
                    ai_metadata={"model": "teste"},
                ),
                ArtifactVersion(
                    artifact_id=artifact.id,
                    number=2,
                    previous_number=1,
                    content=V2,
                    origin=ArtifactOrigin.HUMANO.value,
                    author_id=editor_id,
                ),
            ]
        )
        session.commit()
        return demand.id, artifact.id


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
                v.origin,
                v.content,
                v.raw_content,
                v.ai_metadata,
                v.author_id,
                v.restored_from_number,
                v.created_at,
            )
            for v in versions
        ]


def _restore(api: TestClient, artifact_id: UUID, number: int, author_id: UUID | str):
    return api.post(
        f"/api/v1/artifacts/{artifact_id}/versions/{number}/restore",
        headers={"X-User-ID": str(author_id)},
    )


def test_restore_creates_a_new_current_version_with_the_chosen_content(
    api: TestClient, engine: Engine, company: UUID
) -> None:
    editor_id = _create_user(engine, name="Ana")
    restorer_id = _create_user(engine, name="Bruno")
    demand_id, artifact_id = _create_artifact(engine, company, editor_id)

    response = _restore(api, artifact_id, 1, restorer_id)

    assert response.status_code == 201, response.text
    body = response.json()
    assert body["number"] == 3
    assert body["structured_content"] == V1
    assert body["origin"] == ArtifactOrigin.HUMANO.value
    assert body["author_id"] == str(restorer_id)
    assert body["restored_from_number"] == 1
    assert body["raw_output"] is None
    assert body["ai_metadata"] is None

    artifact = api.get(f"/api/v1/demands/{demand_id}/artifacts").json()[0]
    versions = artifact["versions"]
    assert [v["number"] for v in versions] == [1, 2, 3]
    assert versions[-1]["structured_content"] == V1  # a vigente e a de maior numero


def test_restore_keeps_every_earlier_version_untouched_and_queryable(
    api: TestClient, engine: Engine, company: UUID
) -> None:
    editor_id = _create_user(engine)
    demand_id, artifact_id = _create_artifact(engine, company, editor_id)
    before = _rows(engine, artifact_id)

    assert _restore(api, artifact_id, 1, editor_id).status_code == 201

    after = _rows(engine, artifact_id)
    assert after[:2] == before
    assert len(after) == 3
    listed = api.get(f"/api/v1/demands/{demand_id}/artifacts").json()[0]["versions"]
    assert listed[0]["structured_content"] == V1
    assert listed[0]["raw_output"] == "resposta bruta do modelo"
    assert listed[1]["structured_content"] == V2
    assert listed[1]["raw_output"] is None
    assert listed[1]["restored_from_number"] is None


def test_the_restored_version_is_the_restoration_event(
    api: TestClient, engine: Engine, company: UUID
) -> None:
    editor_id = _create_user(engine)
    restorer_id = _create_user(engine, name="Bruno")
    _, artifact_id = _create_artifact(engine, company, editor_id)

    _restore(api, artifact_id, 1, restorer_id)
    _restore(api, artifact_id, 2, editor_id)

    third, fourth = _rows(engine, artifact_id)[2:]
    # (id, number, origin, content, raw, ai, author, restored_from, created_at)
    assert (third[1], third[6], third[7]) == (3, restorer_id, 1)
    assert (fourth[1], fourth[6], fourth[7]) == (4, editor_id, 2)
    assert third[8] is not None


def test_restoring_the_current_version_is_refused(
    api: TestClient, engine: Engine, company: UUID
) -> None:
    editor_id = _create_user(engine)
    _, artifact_id = _create_artifact(engine, company, editor_id)

    response = _restore(api, artifact_id, 2, editor_id)

    assert response.status_code == 409
    assert response.json()["error"]["code"] == "ARTIFACT_VERSION_ALREADY_CURRENT"
    assert len(_rows(engine, artifact_id)) == 2


def test_restoring_a_missing_version_is_not_found(
    api: TestClient, engine: Engine, company: UUID
) -> None:
    editor_id = _create_user(engine)
    _, artifact_id = _create_artifact(engine, company, editor_id)

    response = _restore(api, artifact_id, 9, editor_id)

    assert response.status_code == 404
    assert response.json()["error"]["code"] == "ARTIFACT_VERSION_NOT_FOUND"
    assert len(_rows(engine, artifact_id)) == 2


def test_unknown_artifact_and_unknown_author_are_not_found(
    api: TestClient, engine: Engine, company: UUID
) -> None:
    editor_id = _create_user(engine)
    _, artifact_id = _create_artifact(engine, company, editor_id)

    missing_artifact = _restore(api, uuid4(), 1, editor_id)
    missing_author = _restore(api, artifact_id, 1, uuid4())

    assert missing_artifact.status_code == 404
    assert missing_artifact.json()["error"]["code"] == "ARTIFACT_NOT_FOUND"
    assert missing_author.status_code == 404
    assert missing_author.json()["error"]["code"] == "USER_NOT_FOUND"
    assert len(_rows(engine, artifact_id)) == 2


def test_author_header_and_version_number_are_validated(
    api: TestClient, engine: Engine, company: UUID
) -> None:
    editor_id = _create_user(engine)
    _, artifact_id = _create_artifact(engine, company, editor_id)

    without_author = api.post(f"/api/v1/artifacts/{artifact_id}/versions/1/restore")
    zero = _restore(api, artifact_id, 0, editor_id)

    assert without_author.status_code == 422
    assert zero.status_code == 422
    assert len(_rows(engine, artifact_id)) == 2


@pytest.mark.parametrize(("number", "restored_from"), [(3, 3), (3, 5), (3, 0)])
def test_database_refuses_a_restoration_pointer_that_is_not_an_earlier_version(
    engine: Engine, company: UUID, number: int, restored_from: int
) -> None:
    """Ponteiro para a propria versao, para uma posterior ou para uma que nao existe (0)."""

    editor_id = _create_user(engine)
    _, artifact_id = _create_artifact(engine, company, editor_id)

    with engine.connect() as connection:
        assert_rejected(
            connection,
            """
            INSERT INTO artifact_versions
                (id, artifact_id, number, previous_number, content, origin, author_id,
                 restored_from_number)
            VALUES (:id, :artifact_id, :number, :number - 1, '{}', 'HUMANO', :author_id,
                    :restored_from)
            """,
            {
                "id": uuid4().hex,
                "artifact_id": artifact_id.hex,
                "number": number,
                "author_id": editor_id.hex,
                "restored_from": restored_from,
            },
        )

    assert len(_rows(engine, artifact_id)) == 2
