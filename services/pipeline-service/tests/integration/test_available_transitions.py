"""Etapas disponiveis a partir da corrente (RF06.3): a interface so habilita o que vale."""

from uuid import UUID, uuid4

import pytest
from fastapi.testclient import TestClient
from sqlalchemy.engine import Engine
from sqlalchemy.orm import Session

from app.domain.enums import DemandStatus, PipelineStage
from app.models.demand import Demand


def _create_demand(
    engine: Engine,
    client_id: UUID,
    *,
    current_stage: PipelineStage = PipelineStage.CAPTACAO,
    status: DemandStatus = DemandStatus.ABERTA,
) -> UUID:
    with Session(engine) as session:
        demand = Demand(
            client_id=client_id,
            title="Demanda",
            current_stage=current_stage.value,
            status=status.value,
        )
        session.add(demand)
        session.commit()
        return demand.id


def _available_transitions(api: TestClient, demand_id: UUID):
    return api.get(f"/api/v1/demands/{demand_id}/available-transitions")


def test_demand_at_captacao_can_only_advance(
    api: TestClient, engine: Engine, company: UUID
) -> None:
    demand_id = _create_demand(engine, company, current_stage=PipelineStage.CAPTACAO)

    response = _available_transitions(api, demand_id)

    assert response.status_code == 200
    body = response.json()
    assert body["current_stage"] == "CAPTACAO"
    assert body["available_stages"] == ["ESTRUTURACAO"]


def test_demand_at_produto_can_advance_or_rollback(
    api: TestClient, engine: Engine, company: UUID
) -> None:
    demand_id = _create_demand(engine, company, current_stage=PipelineStage.PRODUTO)

    body = _available_transitions(api, demand_id).json()

    assert body["current_stage"] == "PRODUTO"
    assert set(body["available_stages"]) == {"CAPTACAO", "ESTRUTURACAO", "PROPOSTA"}


def test_closed_demand_has_no_available_transitions(
    api: TestClient, engine: Engine, company: UUID
) -> None:
    demand_id = _create_demand(
        engine,
        company,
        current_stage=PipelineStage.PRODUTO,
        status=DemandStatus.GANHA,
    )

    body = _available_transitions(api, demand_id).json()

    assert body["current_stage"] == "PRODUTO"
    assert body["available_stages"] == []


def test_available_transitions_of_an_unknown_demand_is_not_found(api: TestClient) -> None:
    response = _available_transitions(api, uuid4())

    assert response.status_code == 404
    assert response.json()["error"]["code"] == "DEMAND_NOT_FOUND"


@pytest.mark.parametrize("method", ["post", "put", "patch", "delete"])
def test_available_transitions_cannot_be_written_through_the_api(
    api: TestClient, engine: Engine, company: UUID, method: str
) -> None:
    demand_id = _create_demand(engine, company)

    response = getattr(api, method)(f"/api/v1/demands/{demand_id}/available-transitions")

    assert response.status_code == 405
