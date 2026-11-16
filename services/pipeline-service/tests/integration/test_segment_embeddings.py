"""Gravacao em lote e busca por similaridade de embeddings de trecho (cards #158/#159).

O que estes testes protegem: o embedding fica vinculado ao trecho com
integridade referencial (card #158); a busca devolve os trechos mais
proximos, ordenados por similaridade, e nunca cruza demanda ou cliente
(card #159, RNF21).
"""

from uuid import UUID, uuid4

import pytest
import sqlalchemy as sa
from fastapi.testclient import TestClient
from sqlalchemy.engine import Engine
from sqlalchemy.orm import Session

from app.models import Demand, RawInput, SegmentEmbedding, SourceSegment, User

MODELO = "sentence-transformers/all-MiniLM-L6-v2"
DIMENSAO = 384


def _vetor(indice_ativo: int, valor: float = 1.0) -> list[float]:
    """Vetor esparso: todo zero, exceto ``valor`` em ``indice_ativo``.

    Dois vetores construidos com indices diferentes sao ortogonais
    (similaridade 0.0); o mesmo indice e o mesmo sinal da similaridade 1.0 -
    controle exato sem depender de um modelo de embedding de verdade.
    """

    vetor = [0.0] * DIMENSAO
    vetor[indice_ativo] = valor
    return vetor


def _create_demand_with_segments(
    engine: Engine, client_id: UUID, quantidade: int = 3
) -> tuple[UUID, list[UUID]]:
    with Session(engine) as session:
        author = User(name="Operador", email=f"{uuid4().hex}@example.com", password_hash="hash")
        session.add(author)
        session.flush()
        demand = Demand(client_id=client_id, title="Demanda com trechos")
        session.add(demand)
        session.flush()
        raw_input = RawInput(
            demand_id=demand.id,
            author_id=author.id,
            received_order=1,
            original_content="texto bruto",
            source="EMAIL",
        )
        session.add(raw_input)
        session.flush()
        segments = [
            SourceSegment(
                id=uuid4(), raw_input_id=raw_input.id, position=i + 1, content=f"trecho {i + 1}"
            )
            for i in range(quantidade)
        ]
        session.add_all(segments)
        session.commit()
        return demand.id, [segment.id for segment in segments]


def _embedding_payload(segment_id: UUID, vetor: list[float], model: str = MODELO) -> dict:
    return {"segment_id": str(segment_id), "model": model, "vector": vetor}


def test_batch_create_persists_and_is_queryable(
    api: TestClient, engine: Engine, company: UUID
) -> None:
    _demand_id, segment_ids = _create_demand_with_segments(engine, company, quantidade=1)

    response = api.post(
        "/api/v1/segment-embeddings",
        json={"embeddings": [_embedding_payload(segment_ids[0], _vetor(0))]},
    )

    assert response.status_code == 201, response.text
    body = response.json()
    assert len(body) == 1
    assert body[0]["segment_id"] == str(segment_ids[0])
    assert body[0]["model"] == MODELO

    with Session(engine) as session:
        saved = session.scalars(sa.select(SegmentEmbedding)).one()
        assert saved.segment_id == segment_ids[0]
        assert saved.vector == _vetor(0)


def test_batch_create_rejects_unknown_segment(
    api: TestClient, engine: Engine, company: UUID
) -> None:
    response = api.post(
        "/api/v1/segment-embeddings",
        json={"embeddings": [_embedding_payload(uuid4(), _vetor(0))]},
    )

    assert response.status_code == 404
    assert response.json()["error"]["code"] == "SOURCE_SEGMENT_NOT_FOUND"


def test_batch_create_rejects_duplicate_pair_in_same_payload(
    api: TestClient, engine: Engine, company: UUID
) -> None:
    _demand_id, segment_ids = _create_demand_with_segments(engine, company, quantidade=1)

    response = api.post(
        "/api/v1/segment-embeddings",
        json={
            "embeddings": [
                _embedding_payload(segment_ids[0], _vetor(0)),
                _embedding_payload(segment_ids[0], _vetor(1)),
            ]
        },
    )

    assert response.status_code == 422


def test_batch_create_rejects_pair_already_persisted(
    api: TestClient, engine: Engine, company: UUID
) -> None:
    _demand_id, segment_ids = _create_demand_with_segments(engine, company, quantidade=1)
    payload = {"embeddings": [_embedding_payload(segment_ids[0], _vetor(0))]}
    assert api.post("/api/v1/segment-embeddings", json=payload).status_code == 201

    response = api.post("/api/v1/segment-embeddings", json=payload)

    assert response.status_code == 409
    assert response.json()["error"]["code"] == "SEGMENT_EMBEDDING_ALREADY_EXISTS"
    with Session(engine) as session:
        assert session.scalar(sa.select(sa.func.count(SegmentEmbedding.segment_id))) == 1


def test_a_second_model_for_the_same_segment_does_not_replace_the_first(
    api: TestClient, engine: Engine, company: UUID
) -> None:
    _demand_id, segment_ids = _create_demand_with_segments(engine, company, quantidade=1)
    api.post(
        "/api/v1/segment-embeddings",
        json={"embeddings": [_embedding_payload(segment_ids[0], _vetor(0), model=MODELO)]},
    )

    response = api.post(
        "/api/v1/segment-embeddings",
        json={"embeddings": [_embedding_payload(segment_ids[0], _vetor(1), model="outro-modelo")]},
    )

    assert response.status_code == 201
    with Session(engine) as session:
        rows = session.scalars(
            sa.select(SegmentEmbedding).where(SegmentEmbedding.segment_id == segment_ids[0])
        ).all()
        assert {row.model for row in rows} == {MODELO, "outro-modelo"}


@pytest.mark.parametrize("vector", [[0.0] * (DIMENSAO - 1), [0.0] * (DIMENSAO + 1)])
def test_batch_create_validates_vector_dimension(
    api: TestClient, engine: Engine, company: UUID, vector: list[float]
) -> None:
    _demand_id, segment_ids = _create_demand_with_segments(engine, company, quantidade=1)

    response = api.post(
        "/api/v1/segment-embeddings",
        json={"embeddings": [_embedding_payload(segment_ids[0], vector)]},
    )

    assert response.status_code == 422


# ----------------------------------------------------------------------
# Busca por similaridade (card #159)
# ----------------------------------------------------------------------


def _search(api: TestClient, demand_id: UUID, vector: list[float], **overrides) -> dict:
    payload: dict = {"model": MODELO, "vector": vector}
    payload.update(overrides)
    response = api.post(f"/api/v1/demands/{demand_id}/segment-embeddings/search", json=payload)
    return response


def test_search_returns_closest_segment_first(
    api: TestClient, engine: Engine, company: UUID
) -> None:
    demand_id, segment_ids = _create_demand_with_segments(engine, company, quantidade=3)
    api.post(
        "/api/v1/segment-embeddings",
        json={
            "embeddings": [
                _embedding_payload(segment_ids[0], _vetor(0)),  # identico a consulta
                _embedding_payload(segment_ids[1], _vetor(1)),  # ortogonal
                _embedding_payload(segment_ids[2], _vetor(0, valor=-1.0)),  # oposto
            ]
        },
    )

    response = _search(api, demand_id, _vetor(0), min_similarity=-1.0)

    assert response.status_code == 200
    results = response.json()["results"]
    assert [r["segment_id"] for r in results] == [
        str(segment_ids[0]),
        str(segment_ids[1]),
        str(segment_ids[2]),
    ]
    assert results[0]["similarity"] == pytest.approx(1.0)
    assert results[1]["similarity"] == pytest.approx(0.0)
    assert results[2]["similarity"] == pytest.approx(-1.0)


def test_search_respects_min_similarity(api: TestClient, engine: Engine, company: UUID) -> None:
    demand_id, segment_ids = _create_demand_with_segments(engine, company, quantidade=2)
    api.post(
        "/api/v1/segment-embeddings",
        json={
            "embeddings": [
                _embedding_payload(segment_ids[0], _vetor(0)),
                _embedding_payload(segment_ids[1], _vetor(1)),
            ]
        },
    )

    response = _search(api, demand_id, _vetor(0), min_similarity=0.5)

    results = response.json()["results"]
    assert len(results) == 1
    assert results[0]["segment_id"] == str(segment_ids[0])


def test_search_respects_top_k(api: TestClient, engine: Engine, company: UUID) -> None:
    demand_id, segment_ids = _create_demand_with_segments(engine, company, quantidade=3)
    api.post(
        "/api/v1/segment-embeddings",
        json={
            "embeddings": [
                _embedding_payload(segment_ids[0], _vetor(0)),
                _embedding_payload(segment_ids[1], _vetor(0, valor=0.9)),
                _embedding_payload(segment_ids[2], _vetor(0, valor=0.8)),
            ]
        },
    )

    response = _search(api, demand_id, _vetor(0), top_k=2, min_similarity=-1.0)

    assert len(response.json()["results"]) == 2


def test_search_never_crosses_demands(api: TestClient, engine: Engine, company: UUID) -> None:
    demand_id, segment_ids = _create_demand_with_segments(engine, company, quantidade=1)
    _other_demand_id, other_segment_ids = _create_demand_with_segments(
        engine, company, quantidade=1
    )
    api.post(
        "/api/v1/segment-embeddings",
        json={
            "embeddings": [
                _embedding_payload(segment_ids[0], _vetor(0)),
                _embedding_payload(other_segment_ids[0], _vetor(0)),
            ]
        },
    )

    response = _search(api, demand_id, _vetor(0), min_similarity=-1.0)

    results = response.json()["results"]
    assert [r["segment_id"] for r in results] == [str(segment_ids[0])]
    assert str(other_segment_ids[0]) not in [r["segment_id"] for r in results]


def test_search_filters_by_model(api: TestClient, engine: Engine, company: UUID) -> None:
    demand_id, segment_ids = _create_demand_with_segments(engine, company, quantidade=1)
    api.post(
        "/api/v1/segment-embeddings",
        json={"embeddings": [_embedding_payload(segment_ids[0], _vetor(0), model="outro-modelo")]},
    )

    response = _search(api, demand_id, _vetor(0), min_similarity=-1.0)

    assert response.json()["results"] == []


def test_search_unknown_demand_is_not_found(api: TestClient, engine: Engine) -> None:
    response = _search(api, uuid4(), _vetor(0))

    assert response.status_code == 404
    assert response.json()["error"]["code"] == "DEMAND_NOT_FOUND"


def test_swagger_documents_segment_embeddings_routes(api: TestClient) -> None:
    document = api.get("/openapi.json").json()
    assert "post" in document["paths"]["/api/v1/segment-embeddings"]
    assert "post" in document["paths"]["/api/v1/demands/{demand_id}/segment-embeddings/search"]
