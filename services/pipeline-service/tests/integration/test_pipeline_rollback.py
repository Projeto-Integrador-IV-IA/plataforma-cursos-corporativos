"""Aceite RF06.2: retrocesso livre, justificado e sem perda de contexto."""

from typing import Any
from uuid import UUID, uuid4

import pytest
import sqlalchemy as sa
from fastapi.testclient import TestClient
from sqlalchemy.engine import Engine
from sqlalchemy.orm import Session

from app.domain.enums import DemandStatus, PipelineStage
from app.models import Demand, StageTransition, User


def _create_user(engine: Engine) -> UUID:
    with Session(engine) as session:
        user = User(name="Operador", email=f"{uuid4().hex}@example.com", password_hash="hash")
        session.add(user)
        session.commit()
        return user.id


def _create_demand(
    engine: Engine,
    client_id: UUID,
    *,
    stage: PipelineStage = PipelineStage.CAPTACAO,
    status: DemandStatus = DemandStatus.ABERTA,
) -> UUID:
    with Session(engine) as session:
        demand = Demand(
            client_id=client_id,
            title="Demanda com mudanca de escopo",
            current_stage=stage.value,
            status=status.value,
        )
        session.add(demand)
        session.commit()
        return demand.id


def _advance(api: TestClient, demand_id: UUID, author_id: UUID):
    return api.post(
        f"/api/v1/demands/{demand_id}/advance",
        headers={"X-User-ID": str(author_id)},
    )


def _rollback(
    api: TestClient,
    demand_id: UUID,
    author_id: UUID,
    to_stage: PipelineStage,
    *,
    reason: str = "Cliente alterou o escopo",
):
    return api.post(
        f"/api/v1/demands/{demand_id}/rollback",
        headers={"X-User-ID": str(author_id)},
        json={"to_stage": to_stage.value, "reason": reason},
    )


def _stage_of(engine: Engine, demand_id: UUID) -> str:
    with Session(engine) as session:
        return session.scalar(sa.select(Demand.current_stage).where(Demand.id == demand_id))


def _events(engine: Engine, demand_id: UUID) -> list[StageTransition]:
    with Session(engine) as session:
        return list(
            session.scalars(
                sa.select(StageTransition).where(StageTransition.demand_id == demand_id)
            ).all()
        )


def test_rollback_then_advance_preserves_the_complete_trail_sources_and_artifacts(
    api: TestClient,
    engine: Engine,
    company: UUID,
) -> None:
    author_id = _create_user(engine)
    demand_id = _create_demand(engine, company)

    source_response = api.post(
        f"/api/v1/demands/{demand_id}/raw-inputs",
        headers={"X-User-ID": str(author_id)},
        json={"original_content": "O cliente pediu outro publico-alvo.", "source": "EMAIL"},
    )
    assert source_response.status_code == 201, source_response.text
    source = source_response.json()

    artifact_response = api.post(
        f"/api/v1/demands/{demand_id}/artifacts",
        json={
            "type": "REQUISITOS_EXTRAIDOS",
            "title": "Escopo inicial",
            "raw_output": '{"publico":"lideranca"}',
            "structured_content": {"publico": "lideranca"},
            "raw_input_ids": [source["id"]],
            "ai_metadata": {"model": "test-model", "prompt": "extract-requirements.v2"},
        },
    )
    assert artifact_response.status_code == 201, artifact_response.text
    artifact = artifact_response.json()

    responses = [_advance(api, demand_id, author_id) for _ in range(3)]
    assert [response.status_code for response in responses] == [200, 200, 200]
    assert _stage_of(engine, demand_id) == PipelineStage.PROPOSTA.value

    rollback_response = _rollback(
        api,
        demand_id,
        author_id,
        PipelineStage.CAPTACAO,
        reason="  Cliente alterou publico e objetivos  ",
    )
    assert rollback_response.status_code == 200, rollback_response.text
    assert rollback_response.json()["reason"] == "Cliente alterou publico e objetivos"
    assert _stage_of(engine, demand_id) == PipelineStage.CAPTACAO.value

    repeated_advance = _advance(api, demand_id, author_id)
    assert repeated_advance.status_code == 200, repeated_advance.text
    assert _stage_of(engine, demand_id) == PipelineStage.ESTRUTURACAO.value

    response_bodies = [
        *(response.json() for response in responses),
        rollback_response.json(),
        repeated_advance.json(),
    ]
    expected_moves = [
        (PipelineStage.CAPTACAO.value, PipelineStage.ESTRUTURACAO.value),
        (PipelineStage.ESTRUTURACAO.value, PipelineStage.PRODUTO.value),
        (PipelineStage.PRODUTO.value, PipelineStage.PROPOSTA.value),
        (PipelineStage.PROPOSTA.value, PipelineStage.CAPTACAO.value),
        (PipelineStage.CAPTACAO.value, PipelineStage.ESTRUTURACAO.value),
    ]
    transition_ids = [UUID(body["transition_id"]) for body in response_bodies]

    persisted_events = _events(engine, demand_id)
    events_by_id = {event.id: event for event in persisted_events}
    assert set(events_by_id) == set(transition_ids)
    assert [
        (events_by_id[event_id].from_stage, events_by_id[event_id].to_stage)
        for event_id in transition_ids
    ] == expected_moves
    occurred_at = [events_by_id[event_id].occurred_at for event_id in transition_ids]
    assert occurred_at == sorted(occurred_at)

    demand_detail = api.get(f"/api/v1/demands/{demand_id}")
    artifacts = api.get(f"/api/v1/demands/{demand_id}/artifacts")
    assert demand_detail.status_code == 200
    assert artifacts.status_code == 200
    preserved_source = demand_detail.json()["raw_inputs"][0]
    for field in ("id", "source", "original_content", "author_id", "truncated", "created_at"):
        assert preserved_source[field] == source[field]
    assert artifacts.json() == [artifact]


@pytest.mark.parametrize(
    "target",
    [PipelineStage.CAPTACAO, PipelineStage.ESTRUTURACAO, PipelineStage.PRODUTO],
)
def test_rollback_accepts_every_stage_before_the_current_one(
    api: TestClient,
    engine: Engine,
    company: UUID,
    target: PipelineStage,
) -> None:
    author_id = _create_user(engine)
    demand_id = _create_demand(engine, company, stage=PipelineStage.PROPOSTA)

    response = _rollback(api, demand_id, author_id, target)

    assert response.status_code == 200, response.text
    assert response.json()["from_stage"] == PipelineStage.PROPOSTA.value
    assert response.json()["current_stage"] == target.value
    assert _stage_of(engine, demand_id) == target.value


@pytest.mark.parametrize(
    "target",
    [PipelineStage.PRODUTO, PipelineStage.PROPOSTA, PipelineStage.ACOMPANHAMENTO],
)
def test_rollback_rejects_the_current_or_a_later_stage(
    api: TestClient,
    engine: Engine,
    company: UUID,
    target: PipelineStage,
) -> None:
    author_id = _create_user(engine)
    demand_id = _create_demand(engine, company, stage=PipelineStage.PRODUTO)

    response = _rollback(api, demand_id, author_id, target)

    assert response.status_code == 409
    assert response.json()["error"]["code"] == "ROLLBACK_TARGET_NOT_PREVIOUS"
    assert _stage_of(engine, demand_id) == PipelineStage.PRODUTO.value
    assert _events(engine, demand_id) == []


@pytest.mark.parametrize(
    "payload",
    [
        None,
        {"to_stage": PipelineStage.CAPTACAO.value},
        {"to_stage": PipelineStage.CAPTACAO.value, "reason": "   "},
    ],
)
def test_rollback_requires_a_reason(
    api: TestClient,
    engine: Engine,
    company: UUID,
    payload: dict[str, Any] | None,
) -> None:
    author_id = _create_user(engine)
    demand_id = _create_demand(engine, company, stage=PipelineStage.PROPOSTA)
    kwargs = {"json": payload} if payload is not None else {}

    response = api.post(
        f"/api/v1/demands/{demand_id}/rollback",
        headers={"X-User-ID": str(author_id)},
        **kwargs,
    )

    assert response.status_code == 422
    assert _stage_of(engine, demand_id) == PipelineStage.PROPOSTA.value
    assert _events(engine, demand_id) == []


def test_closed_demand_does_not_rollback(
    api: TestClient,
    engine: Engine,
    company: UUID,
) -> None:
    author_id = _create_user(engine)
    demand_id = _create_demand(
        engine,
        company,
        stage=PipelineStage.PROPOSTA,
        status=DemandStatus.GANHA,
    )

    response = _rollback(api, demand_id, author_id, PipelineStage.CAPTACAO)

    assert response.status_code == 409
    assert response.json()["error"]["code"] == "DEMAND_NOT_OPEN"
    assert _stage_of(engine, demand_id) == PipelineStage.PROPOSTA.value
    assert _events(engine, demand_id) == []


def test_rollback_is_declared_in_swagger(api: TestClient) -> None:
    document = api.get("/openapi.json").json()
    operation = document["paths"]["/api/v1/demands/{demand_id}/rollback"]["post"]

    assert operation["requestBody"]["required"] is True
    assert {"200", "404", "409", "422"} <= set(operation["responses"])
    schema = document["components"]["schemas"]["RollbackRequest"]
    assert set(schema["required"]) == {"to_stage", "reason"}
    assert schema["additionalProperties"] is False
