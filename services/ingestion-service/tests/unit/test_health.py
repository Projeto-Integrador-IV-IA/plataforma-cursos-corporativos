"""Testes do endpoint de liveness do ingestion-service (RNF01)."""

from fastapi.testclient import TestClient


def test_health_reports_service_is_up(client: TestClient) -> None:
    response = client.get("/health")

    assert response.status_code == 200
    assert response.json() == {"status": "ok", "service": "ingestion-service"}


def test_health_stays_outside_versioned_api(client: TestClient) -> None:
    assert client.get("/api/v1/health").status_code == 404
