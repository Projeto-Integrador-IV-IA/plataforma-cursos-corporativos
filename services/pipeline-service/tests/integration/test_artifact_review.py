"""Decisao de revisao humana sobre uma versao de artefato (RF19.2, cards #58-#60).

A decisao e sobre uma versao especifica, append-only como as demais trilhas do
servico: aprovar, rejeitar ou devolver registra quem decidiu, quando e com que
justificativa, sem apagar nem alterar nada que ja existia.
"""

from uuid import UUID, uuid4

from fastapi.testclient import TestClient
from sqlalchemy.engine import Engine
from sqlalchemy.orm import Session

from app.domain.enums import ArtifactOrigin, ArtifactType
from app.models import Artifact, ArtifactVersion
from app.models.demand import Demand
from app.models.user import User

V1 = {"tema": "Lideranca", "carga_horaria": None}


def _create_user(engine: Engine, name: str = "Operador") -> UUID:
    with Session(engine) as session:
        user = User(name=name, email=f"{uuid4().hex}@example.com", password_hash="hash")
        session.add(user)
        session.commit()
        return user.id


def _create_artifact(engine: Engine, client_id: UUID) -> tuple[UUID, UUID]:
    with Session(engine) as session:
        demand = Demand(client_id=client_id, title="Demanda")
        session.add(demand)
        session.flush()
        artifact = Artifact(
            demand_id=demand.id, type=ArtifactType.REQUISITOS_EXTRAIDOS.value, title="Ementa"
        )
        session.add(artifact)
        session.flush()
        session.add(
            ArtifactVersion(
                artifact_id=artifact.id,
                number=1,
                raw_content="resposta bruta do modelo",
                content=V1,
                origin=ArtifactOrigin.IA.value,
                ai_metadata={"model": "teste"},
            )
        )
        session.commit()
        return demand.id, artifact.id


def _review(
    api: TestClient,
    artifact_id: UUID,
    *,
    version_number: int,
    decision: str,
    author_id: UUID | str,
    reason: str | None = None,
):
    payload: dict[str, object] = {"version_number": version_number, "decision": decision}
    if reason is not None:
        payload["reason"] = reason
    return api.post(
        f"/api/v1/artifacts/{artifact_id}/review",
        json=payload,
        headers={"X-User-ID": str(author_id)},
    )


def test_approving_the_current_version_does_not_require_a_reason(
    api: TestClient, engine: Engine, company: UUID
) -> None:
    author_id = _create_user(engine)
    _, artifact_id = _create_artifact(engine, company)

    response = _review(api, artifact_id, version_number=1, decision="APROVADO", author_id=author_id)

    assert response.status_code == 201, response.text
    body = response.json()
    assert body["decision"] == "APROVADO"
    assert body["version_number"] == 1
    assert body["reason"] is None
    assert body["author_id"] == str(author_id)
    assert body["created_at"]


def test_rejecting_without_a_reason_is_refused(
    api: TestClient, engine: Engine, company: UUID
) -> None:
    author_id = _create_user(engine)
    _, artifact_id = _create_artifact(engine, company)

    response = _review(
        api, artifact_id, version_number=1, decision="REJEITADO", author_id=author_id
    )

    assert response.status_code == 422
    assert response.json()["error"]["code"] == "VALIDATION_ERROR"


def test_returning_requires_a_non_blank_reason(
    api: TestClient, engine: Engine, company: UUID
) -> None:
    author_id = _create_user(engine)
    _, artifact_id = _create_artifact(engine, company)

    blank = _review(
        api, artifact_id, version_number=1, decision="DEVOLVIDO", author_id=author_id, reason="   "
    )
    filled = _review(
        api,
        artifact_id,
        version_number=1,
        decision="DEVOLVIDO",
        author_id=author_id,
        reason="Falta detalhar a carga horaria.",
    )

    assert blank.status_code == 422
    assert filled.status_code == 201, filled.text
    assert filled.json()["reason"] == "Falta detalhar a carga horaria."


def test_reviewing_a_version_that_is_no_longer_current_is_refused(
    api: TestClient, engine: Engine, company: UUID
) -> None:
    """Editar depois que a tela abriu nao pode deixar a aprovacao valer para o texto antigo."""

    editor_id = _create_user(engine, name="Ana")
    author_id = _create_user(engine, name="Bruno")
    _, artifact_id = _create_artifact(engine, company)

    assert (
        api.post(
            f"/api/v1/artifacts/{artifact_id}/versions",
            json={
                "base_version_number": 1,
                "structured_content": {"tema": "Lideranca para gestores"},
            },
            headers={"X-User-ID": str(editor_id)},
        ).status_code
        == 201
    )

    response = _review(api, artifact_id, version_number=1, decision="APROVADO", author_id=author_id)

    assert response.status_code == 409
    assert response.json()["error"]["code"] == "ARTIFACT_VERSION_STALE"


def test_unknown_artifact_and_unknown_author_are_not_found(
    api: TestClient, engine: Engine, company: UUID
) -> None:
    author_id = _create_user(engine)
    _, artifact_id = _create_artifact(engine, company)

    missing_artifact = _review(
        api, uuid4(), version_number=1, decision="APROVADO", author_id=author_id
    )
    missing_author = _review(
        api, artifact_id, version_number=1, decision="APROVADO", author_id=uuid4()
    )

    assert missing_artifact.status_code == 404
    assert missing_artifact.json()["error"]["code"] == "ARTIFACT_NOT_FOUND"
    assert missing_author.status_code == 404
    assert missing_author.json()["error"]["code"] == "USER_NOT_FOUND"


def test_review_history_is_listed_from_oldest_to_newest(
    api: TestClient, engine: Engine, company: UUID
) -> None:
    author_id = _create_user(engine)
    _, artifact_id = _create_artifact(engine, company)

    _review(
        api,
        artifact_id,
        version_number=1,
        decision="DEVOLVIDO",
        author_id=author_id,
        reason="Falta a carga horaria.",
    )
    _review(api, artifact_id, version_number=1, decision="APROVADO", author_id=author_id)

    history = api.get(f"/api/v1/artifacts/{artifact_id}/reviews")

    assert history.status_code == 200
    decisions = [item["decision"] for item in history.json()]
    assert decisions == ["DEVOLVIDO", "APROVADO"]


def test_artifact_exposes_the_latest_review_decision(
    api: TestClient, engine: Engine, company: UUID
) -> None:
    author_id = _create_user(engine)
    demand_id, artifact_id = _create_artifact(engine, company)

    before = api.get(f"/api/v1/demands/{demand_id}/artifacts").json()[0]
    assert before["latest_review"] is None

    _review(
        api,
        artifact_id,
        version_number=1,
        decision="DEVOLVIDO",
        author_id=author_id,
        reason="Falta a carga horaria.",
    )

    after = api.get(f"/api/v1/demands/{demand_id}/artifacts").json()[0]
    assert after["latest_review"]["decision"] == "DEVOLVIDO"
    assert after["latest_review"]["reason"] == "Falta a carga horaria."


def test_author_header_and_body_are_validated(
    api: TestClient, engine: Engine, company: UUID
) -> None:
    author_id = _create_user(engine)
    _, artifact_id = _create_artifact(engine, company)

    without_author = api.post(
        f"/api/v1/artifacts/{artifact_id}/review",
        json={"version_number": 1, "decision": "APROVADO"},
    )
    invalid_decision = _review(
        api, artifact_id, version_number=1, decision="TALVEZ", author_id=author_id
    )
    zero_version = _review(
        api, artifact_id, version_number=0, decision="APROVADO", author_id=author_id
    )

    assert without_author.status_code == 422
    assert invalid_decision.status_code == 422
    assert zero_version.status_code == 422
