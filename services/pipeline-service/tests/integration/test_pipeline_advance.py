"""Aceite do avanco de etapa (RF06) e da trilha que ele alimenta (RF07).

Cobre os criterios do card: transicao aplicada e registrada, atomicidade,
recusa na ultima etapa e ausencia de caminho que altere ou apague a trilha.
"""

from uuid import UUID, uuid4

import pytest
import sqlalchemy as sa
from fastapi.testclient import TestClient
from sqlalchemy.engine import Engine
from sqlalchemy.orm import Session

from app.domain.enums import DemandStatus, PipelineStage
from app.models.demand import Demand
from app.models.stage_transition import StageTransition
from app.models.user import User
from app.repositories.demand_repository import DemandRepository
from app.repositories.transition_repository import TransitionRepository

ORDER = [stage.value for stage in PipelineStage]


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
            title="Demanda",
            current_stage=stage.value,
            status=status.value,
        )
        session.add(demand)
        session.commit()
        return demand.id


def _stage_of(engine: Engine, demand_id: UUID) -> str:
    with Session(engine) as session:
        return session.scalar(sa.select(Demand.current_stage).where(Demand.id == demand_id))


def _trail(engine: Engine, demand_id: UUID) -> list[tuple[str | None, str, UUID, str | None]]:
    with Session(engine) as session:
        rows = session.execute(
            sa.select(
                StageTransition.from_stage,
                StageTransition.to_stage,
                StageTransition.author_id,
                StageTransition.reason,
            ).where(StageTransition.demand_id == demand_id)
        ).all()
        return [tuple(row) for row in rows]


def _advance(api: TestClient, demand_id: UUID, author_id: UUID, **kwargs: object):
    return api.post(
        f"/api/v1/demands/{demand_id}/advance",
        headers={"X-User-ID": str(author_id)},
        **kwargs,
    )


def test_advance_walks_the_pipeline_with_one_trail_event_per_transition(
    api: TestClient, engine: Engine, company: UUID
) -> None:
    author_id = _create_user(engine)
    demand_id = _create_demand(engine, company)
    expected = list(zip(ORDER, ORDER[1:], strict=False))

    for index, (origin, destination) in enumerate(expected):
        # A primeira chamada leva justificativa; as demais vao sem corpo.
        kwargs = {"json": {"reason": "  Cliente validou o escopo  "}} if index == 0 else {}
        response = _advance(api, demand_id, author_id, **kwargs)

        assert response.status_code == 200, response.text
        body = response.json()
        assert body["demand_id"] == str(demand_id)
        assert body["from_stage"] == origin
        assert body["current_stage"] == destination
        assert body["author_id"] == str(author_id)
        assert body["reason"] == ("Cliente validou o escopo" if index == 0 else None)
        assert _stage_of(engine, demand_id) == destination

    trail = _trail(engine, demand_id)
    assert len(trail) == len(expected)
    assert sorted((origin, destination) for origin, destination, _, _ in trail) == sorted(expected)
    assert {author for _, _, author, _ in trail} == {author_id}

    refused = _advance(api, demand_id, author_id)

    assert refused.status_code == 409
    error = refused.json()["error"]
    assert error["code"] == "DEMAND_AT_FINAL_STAGE"
    assert PipelineStage.ACOMPANHAMENTO.value in error["message"]
    assert _stage_of(engine, demand_id) == PipelineStage.ACOMPANHAMENTO.value
    assert len(_trail(engine, demand_id)) == len(expected)


def test_failure_after_recording_leaves_neither_stage_nor_trail_changed(
    api: TestClient,
    engine: Engine,
    company: UUID,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    author_id = _create_user(engine)
    demand_id = _create_demand(engine, company)

    def broken_update(self: DemandRepository, demand: Demand, changes: object) -> Demand:
        raise RuntimeError("falha simulada depois de gravar a transicao")

    # O servico grava a transicao e so depois atualiza a demanda: falhar na
    # segunda metade prova que a primeira nao sobrevive sozinha.
    monkeypatch.setattr(DemandRepository, "update", broken_update)

    with pytest.raises(RuntimeError):
        _advance(api, demand_id, author_id)

    assert _stage_of(engine, demand_id) == PipelineStage.CAPTACAO.value
    assert _trail(engine, demand_id) == []


def test_closed_demand_does_not_advance(api: TestClient, engine: Engine, company: UUID) -> None:
    author_id = _create_user(engine)
    demand_id = _create_demand(engine, company, status=DemandStatus.GANHA)

    response = _advance(api, demand_id, author_id)

    assert response.status_code == 409
    assert response.json()["error"]["code"] == "DEMAND_NOT_OPEN"
    assert _stage_of(engine, demand_id) == PipelineStage.CAPTACAO.value
    assert _trail(engine, demand_id) == []


def test_unknown_demand_is_not_found(api: TestClient, engine: Engine) -> None:
    author_id = _create_user(engine)

    response = _advance(api, uuid4(), author_id)

    assert response.status_code == 404
    assert response.json()["error"]["code"] == "DEMAND_NOT_FOUND"


def test_unknown_author_is_not_found_and_changes_nothing(
    api: TestClient, engine: Engine, company: UUID
) -> None:
    demand_id = _create_demand(engine, company)

    response = _advance(api, demand_id, uuid4())

    assert response.status_code == 404
    assert response.json()["error"]["code"] == "USER_NOT_FOUND"
    assert _stage_of(engine, demand_id) == PipelineStage.CAPTACAO.value
    assert _trail(engine, demand_id) == []


def test_author_header_is_required(api: TestClient, engine: Engine, company: UUID) -> None:
    demand_id = _create_demand(engine, company)

    response = api.post(f"/api/v1/demands/{demand_id}/advance")

    assert response.status_code == 422
    assert _trail(engine, demand_id) == []


def test_trail_has_no_update_or_delete_path(api: TestClient) -> None:
    public = {name for name in dir(TransitionRepository) if not name.startswith("_")}
    assert "record" in public
    assert not {
        name for name in public if name.startswith(("update", "delete", "remove", "edit"))
    }

    paths = api.app.openapi()["paths"]
    for path, operations in paths.items():
        if "transition" in path or path.endswith("/advance"):
            assert not set(operations) & {"put", "patch", "delete"}, path
