"""Aceite de POST /api/v1/demands/{demand_id}/embeddings (card #160, RF29).

A rota em si e fina - o que este teste protege e a fiacao: o endpoint chama o
caso de uso certo e devolve o DTO esperado, sem tocar rede de verdade (a
dependencia e substituida por uma dubla, no mesmo estilo de
``test_structuring_jobs.py``).
"""

from collections.abc import Iterator
from typing import Any

import pytest
from fastapi.testclient import TestClient

from app.api.v1.routes.embeddings import get_embedding_service
from app.main import create_app
from app.providers.mock_embedding_provider import MockEmbeddingProvider
from app.services.embedding_service import EmbeddingService


class _ClientFalso:
    def __init__(self, segmentos: list[dict[str, Any]]) -> None:
        self._segmentos = segmentos

    async def list_demand_segments(self, demand_id: str) -> list[dict[str, Any]]:
        return self._segmentos

    async def save_segment_embeddings(self, embeddings: list[dict[str, Any]]) -> None:
        pass


@pytest.fixture
def client() -> Iterator[TestClient]:
    aplicacao = create_app()
    segmentos = [
        {"id": "seg-1", "content": "primeiro trecho"},
        {"id": "seg-2", "content": "segundo trecho"},
    ]
    service = EmbeddingService(MockEmbeddingProvider(model="mock"), _ClientFalso(segmentos))
    aplicacao.dependency_overrides[get_embedding_service] = lambda: service
    with TestClient(aplicacao) as test_client:
        yield test_client
    aplicacao.dependency_overrides.clear()


def test_embed_demand_returns_how_many_segments_were_processed(client: TestClient) -> None:
    resposta = client.post("/api/v1/demands/dem-42/embeddings")

    assert resposta.status_code == 200
    corpo = resposta.json()
    assert corpo["demand_id"] == "dem-42"
    assert corpo["model"] == "mock"
    assert corpo["segments_embedded"] == 2


def test_swagger_documents_the_embeddings_route(client: TestClient) -> None:
    documento = client.get("/openapi.json").json()

    assert "post" in documento["paths"]["/api/v1/demands/{demand_id}/embeddings"]
