"""Aceite da persistencia e consulta de trechos por fonte e demanda (issue 151)."""

from uuid import UUID, uuid4

import pytest
import sqlalchemy as sa
from fastapi.testclient import TestClient
from sqlalchemy.engine import Connection, Engine
from sqlalchemy.orm import Session

from app.models import Demand, RawInput, SourceSegment, User

from ._schema import (
    DEMAND_ID,
    RAW_INPUT_ID,
    USER_ID,
    assert_rejected,
    insert_client,
    insert_demand,
    insert_user,
)

SEGMENT_IDS = (
    UUID("4d6bbfc3-58db-5828-a4e3-e777774b10e8"),
    UUID("2cf6fe08-8db2-5194-afb1-7f9d85e855d0"),
)


@pytest.fixture
def operator(engine: Engine) -> UUID:
    with Session(engine) as session:
        user = User(name="Operadora", email="segmentos@example.com", password_hash="hash")
        session.add(user)
        session.commit()
        return user.id


@pytest.fixture
def demand(engine: Engine, company: UUID) -> UUID:
    with Session(engine) as session:
        demand = Demand(client_id=company, title="Curso com evidencias")
        session.add(demand)
        session.commit()
        return demand.id


@pytest.fixture
def raw_input(engine: Engine, demand: UUID, operator: UUID) -> UUID:
    with Session(engine) as session:
        source = RawInput(
            demand_id=demand,
            author_id=operator,
            received_order=1,
            original_content="Primeiro trecho\nSegundo trecho",
            normalized_content="Primeiro trecho\nSegundo trecho",
            source="ANOTACAO",
        )
        session.add(source)
        session.commit()
        return source.id


def segment_batch() -> dict[str, list[dict[str, str | int]]]:
    return {
        "segments": [
            {"id": str(SEGMENT_IDS[1]), "position": 2, "content": "Segundo trecho"},
            {"id": str(SEGMENT_IDS[0]), "position": 1, "content": "Primeiro trecho"},
        ]
    }


def test_segments_are_persisted_and_returned_in_source_order(
    api: TestClient,
    engine: Engine,
    raw_input: UUID,
    demand: UUID,
) -> None:
    response = api.post(f"/api/v1/raw-inputs/{raw_input}/segments", json=segment_batch())

    assert response.status_code == 201, response.text
    body = response.json()
    assert [item["position"] for item in body] == [1, 2]
    assert [item["content"] for item in body] == ["Primeiro trecho", "Segundo trecho"]
    assert {item["raw_input_id"] for item in body} == {str(raw_input)}
    assert {item["demand_id"] for item in body} == {str(demand)}

    with Session(engine) as session:
        stored = session.query(SourceSegment).order_by(SourceSegment.position).all()
        assert [item.id for item in stored] == list(SEGMENT_IDS)


def test_segments_are_recoverable_by_source_and_demand(
    api: TestClient,
    raw_input: UUID,
    demand: UUID,
) -> None:
    api.post(f"/api/v1/raw-inputs/{raw_input}/segments", json=segment_batch())

    by_source = api.get(f"/api/v1/raw-inputs/{raw_input}/segments")
    by_demand = api.get(f"/api/v1/demands/{demand}/segments")

    assert by_source.status_code == 200
    assert by_demand.status_code == 200
    assert by_source.json() == by_demand.json()
    assert [item["id"] for item in by_source.json()] == [str(item) for item in SEGMENT_IDS]


def test_replaying_the_same_stable_segments_is_idempotent(
    api: TestClient,
    engine: Engine,
    raw_input: UUID,
) -> None:
    first = api.post(f"/api/v1/raw-inputs/{raw_input}/segments", json=segment_batch())
    replay = api.post(f"/api/v1/raw-inputs/{raw_input}/segments", json=segment_batch())

    assert first.status_code == replay.status_code == 201
    assert first.json() == replay.json()
    with Session(engine) as session:
        assert session.query(SourceSegment).count() == 2


@pytest.mark.parametrize(
    ("field", "value"),
    (("position", 0), ("content", "   ")),
)
def test_invalid_segment_is_rejected_without_partial_persistence(
    api: TestClient,
    engine: Engine,
    raw_input: UUID,
    field: str,
    value: str | int,
) -> None:
    payload = segment_batch()
    payload["segments"][1][field] = value

    response = api.post(f"/api/v1/raw-inputs/{raw_input}/segments", json=payload)

    assert response.status_code == 422
    with Session(engine) as session:
        assert session.query(SourceSegment).count() == 0


def test_position_or_id_cannot_be_reused_for_different_evidence(
    api: TestClient,
    raw_input: UUID,
) -> None:
    api.post(f"/api/v1/raw-inputs/{raw_input}/segments", json=segment_batch())
    payload = {
        "segments": [
            {"id": str(uuid4()), "position": 1, "content": "Trecho substituto"},
        ]
    }

    response = api.post(f"/api/v1/raw-inputs/{raw_input}/segments", json=payload)

    assert response.status_code == 409
    assert response.json()["error"]["code"] == "SOURCE_SEGMENT_CONFLICT"


def test_unknown_source_and_demand_are_reported(api: TestClient) -> None:
    missing_source = uuid4()
    missing_demand = uuid4()

    create = api.post(
        f"/api/v1/raw-inputs/{missing_source}/segments",
        json={
            "segments": [
                {"id": str(uuid4()), "position": 1, "content": "Trecho"},
            ]
        },
    )
    by_source = api.get(f"/api/v1/raw-inputs/{missing_source}/segments")
    by_demand = api.get(f"/api/v1/demands/{missing_demand}/segments")

    assert create.status_code == by_source.status_code == by_demand.status_code == 404
    assert create.json()["error"]["code"] == "RAW_INPUT_NOT_FOUND"
    assert by_demand.json()["error"]["code"] == "DEMAND_NOT_FOUND"


def test_database_rejects_orphan_segment(database: Connection) -> None:
    assert_rejected(
        database,
        """
        INSERT INTO source_segments (id, raw_input_id, position, content)
        VALUES (:id, :raw_input_id, 1, 'Trecho orfao')
        """,
        {"id": SEGMENT_IDS[0].hex, "raw_input_id": uuid4().hex},
    )


def test_source_with_segments_cannot_be_deleted(
    database: Connection,
) -> None:
    insert_user(database)
    insert_client(database)
    insert_demand(database)
    database.execute(
        sa.text(
            """
            INSERT INTO raw_inputs
                (id, demand_id, original_content, received_order, source, author_id)
            VALUES (:id, :demand_id, 'Conteudo', 1, 'EMAIL', :author_id)
            """
        ),
        {"id": RAW_INPUT_ID, "demand_id": DEMAND_ID, "author_id": USER_ID},
    )
    database.execute(
        sa.text(
            """
            INSERT INTO source_segments (id, raw_input_id, position, content)
            VALUES (:id, :raw_input_id, 1, 'Trecho')
            """
        ),
        {"id": SEGMENT_IDS[0].hex, "raw_input_id": RAW_INPUT_ID},
    )
    database.commit()

    assert_rejected(
        database,
        "DELETE FROM raw_inputs WHERE id = :id",
        {"id": RAW_INPUT_ID},
    )
