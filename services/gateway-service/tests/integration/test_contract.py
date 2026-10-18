"""O contrato versionado acompanha exatamente o gateway publicado (RNF02)."""

from pathlib import Path

import yaml
from fastapi.testclient import TestClient

CONTRACT = Path(__file__).resolve().parents[4] / "packages/contracts/openapi/gateway-service.yaml"


def test_gateway_openapi_matches_the_versioned_contract(client: TestClient) -> None:
    declared = yaml.safe_load(CONTRACT.read_text(encoding="utf-8"))
    published = client.get("/openapi.json").json()

    assert declared == published
