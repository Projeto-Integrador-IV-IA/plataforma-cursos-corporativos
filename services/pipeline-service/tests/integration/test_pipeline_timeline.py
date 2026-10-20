"""Linha do tempo de etapas da demanda (RF07): toda movimentacao aparece nela."""

from datetime import UTC, datetime
from uuid import UUID, uuid4

import pytest
from fastapi.testclient import TestClient
from sqlalchemy.engine import Engine
from sqlalchemy.orm import Session

from app.domain.enums import PipelineStage
from app.models.demand import Demand
from app.models.stage_transition import StageTransition
from app.models.user import User

ORDER = [stage.value for stage in PipelineStage]


def _create_user(engine: Engine, name: str = "Operador") -> UUID:
    with Session(engine) as session:
        user = User(name=name, email=f"{uuid4().hex}@example.com", password_hash="hash")
        session.add(user)
        session.commit()
        return user.id


def _create_demand(engine: Engine, client_id: UUID) -> UUID:
    with Session(engine) as session:
        demand = Demand(client_id=client_id, title="Demanda")
        session.add(demand)
        session.commit()
        return demand.id


def _timeline(api: TestClient, demand_id: UUID):
    return api.get(f"/api/v1/demands/{demand_id}/transitions")


def test_every_advance_shows_up_in_the_timeline_with_origin_destination_author_and_time(
    api: TestClient, engine: Engine, company: UUID
) -> None:
    author_id = _create_user(engine, name="Ana Operadora")
    demand_id = _create_demand(engine, company)
    for index in range(3):
        response = api.post(
            f"/api/v1/demands/{demand_id}/advance",
            headers={"X-User-ID": str(author_id)},
            json={"reason": "primeiro avanco"} if index == 0 else None,
        )
        assert response.status_code == 200, response.text

    response = _timeline(api, demand_id)

    assert response.status_code == 200
    body = response.json()
    assert body["total"] == 3
    # Os tres avancos podem cair no mesmo segundo no SQLite: compara como conjunto.
    assert {(item["from_stage"], item["to_stage"]) for item in body["items"]} == set(
        zip(ORDER, ORDER[1:4], strict=True)
    )
    for item in body["items"]:
        assert item["demand_id"] == str(demand_id)
        assert item["author"] == {"id": str(author_id), "name": "Ana Operadora"}
        assert item["occurred_at"]
    reasons = {item["to_stage"]: item["reason"] for item in body["items"]}
    assert reasons[PipelineStage.ESTRUTURACAO.value] == "primeiro avanco"


def test_timeline_is_empty_for_a_demand_without_moves(
    api: TestClient, engine: Engine, company: UUID
) -> None:
    demand_id = _create_demand(engine, company)

    response = _timeline(api, demand_id)

    assert response.status_code == 200
    assert response.json() == {"items": [], "total": 0}


def test_timeline_of_an_unknown_demand_is_not_found(api: TestClient) -> None:
    response = _timeline(api, uuid4())

    assert response.status_code == 404
    assert response.json()["error"]["code"] == "DEMAND_NOT_FOUND"


def test_timeline_is_ordered_from_oldest_to_newest(
    api: TestClient, engine: Engine, company: UUID
) -> None:
    author_id = _create_user(engine)
    demand_id = _create_demand(engine, company)
    moments = [
        (PipelineStage.PRODUTO, PipelineStage.CAPTACAO, datetime(2026, 10, 3, 9, tzinfo=UTC)),
        (PipelineStage.CAPTACAO, PipelineStage.ESTRUTURACAO, datetime(2026, 10, 1, 9, tzinfo=UTC)),
        (PipelineStage.ESTRUTURACAO, PipelineStage.PRODUTO, datetime(2026, 10, 2, 9, tzinfo=UTC)),
    ]
    with Session(engine) as session:
        # Gravados fora de ordem de proposito: a ordem da resposta vem do instante.
        for origin, destination, occurred_at in moments:
            session.add(
                StageTransition(
                    demand_id=demand_id,
                    from_stage=origin.value,
                    to_stage=destination.value,
                    author_id=author_id,
                    occurred_at=occurred_at,
                )
            )
        session.commit()

    items = _timeline(api, demand_id).json()["items"]

    assert [item["to_stage"] for item in items] == ["ESTRUTURACAO", "PRODUTO", "CAPTACAO"]


@pytest.mark.parametrize("method", ["put", "patch", "delete"])
def test_timeline_cannot_be_written_through_the_api(
    api: TestClient, engine: Engine, company: UUID, method: str
) -> None:
    demand_id = _create_demand(engine, company)

    response = getattr(api, method)(f"/api/v1/demands/{demand_id}/transitions")

    assert response.status_code == 405
