"""Edicao humana de artefatos: cada salvamento cria uma versao nova."""

from uuid import UUID, uuid4

import sqlalchemy as sa
from fastapi.testclient import TestClient
from sqlalchemy.engine import Engine
from sqlalchemy.orm import Session

from app.domain.enums import ArtifactOrigin, ArtifactType
from app.models import Artifact, ArtifactVersion, Demand, User


def _create_artifact(engine: Engine, client_id: UUID) -> tuple[UUID, UUID, UUID]:
    with Session(engine) as session:
        user = User(name="Revisora", email=f"{uuid4().hex}@example.com", password_hash="hash")
        demand = Demand(client_id=client_id, title="Demanda para revisao")
        session.add_all([user, demand])
        session.flush()
        artifact = Artifact(
            demand_id=demand.id,
            type=ArtifactType.REQUISITOS_EXTRAIDOS.value,
            title="Requisitos",
        )
        session.add(artifact)
        session.flush()
        session.add(
            ArtifactVersion(
                artifact_id=artifact.id,
                number=1,
                raw_content="resposta original da IA",
                content={"tema": "Lideranca", "carga_horaria": None},
                origin=ArtifactOrigin.IA.value,
                ai_metadata={"model": "teste"},
            )
        )
        session.commit()
        return demand.id, artifact.id, user.id


def test_edit_saves_new_human_version_linked_to_ai_origin(
    api: TestClient, engine: Engine, company: UUID
) -> None:
    demand_id, artifact_id, editor_id = _create_artifact(engine, company)

    response = api.patch(
        f"/api/v1/artifacts/{artifact_id}/versions/1",
        headers={"X-User-ID": str(editor_id)},
        json={"structured_content": {"tema": "Lideranca", "carga_horaria": 40}},
    )

    assert response.status_code == 201, response.text
    edited = response.json()
    assert edited["number"] == 2
    assert edited["origin"] == ArtifactOrigin.HUMANO.value
    assert edited["origin_number"] == 1
    assert edited["previous_number"] == 1
    assert edited["author_id"] == str(editor_id)
    assert edited["raw_output"] is None

    versions = api.get(f"/api/v1/artifacts/{artifact_id}/versions").json()
    assert [version["number"] for version in versions] == [1, 2]
    assert versions[0]["structured_content"] == {"tema": "Lideranca", "carga_horaria": None}
    assert versions[0]["raw_output"] == "resposta original da IA"
    assert versions[1]["structured_content"] == {"tema": "Lideranca", "carga_horaria": 40}

    detail = api.get(f"/api/v1/demands/{demand_id}/artifacts").json()[0]
    assert [version["number"] for version in detail["versions"]] == [1, 2]


def test_editing_human_version_keeps_the_original_ai_link(
    api: TestClient, engine: Engine, company: UUID
) -> None:
    _, artifact_id, editor_id = _create_artifact(engine, company)

    first = api.patch(
        f"/api/v1/artifacts/{artifact_id}/versions/1",
        headers={"X-User-ID": str(editor_id)},
        json={"structured_content": {"tema": "Primeira revisao"}},
    )
    assert first.status_code == 201, first.text

    second = api.patch(
        f"/api/v1/artifacts/{artifact_id}/versions/2",
        headers={"X-User-ID": str(editor_id)},
        json={"structured_content": {"tema": "Segunda revisao"}},
    )
    assert second.status_code == 201, second.text
    assert second.json()["number"] == 3
    assert second.json()["origin_number"] == 1

    with Session(engine) as session:
        rows = session.scalars(
            sa.select(ArtifactVersion)
            .where(ArtifactVersion.artifact_id == artifact_id)
            .order_by(ArtifactVersion.number)
        ).all()
        assert [row.origin_number for row in rows] == [None, 1, 1]
