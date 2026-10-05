"""O contrato publicado do ingestion-service acompanha o codigo (RNF02).

Sem esta verificacao o arquivo em ``packages/contracts`` vira documentacao
optativa: ele ficou como ``paths: {}`` enquanto o servico ja tinha rota.
"""

from pathlib import Path

import yaml
from fastapi.testclient import TestClient

CONTRATO = Path(__file__).resolve().parents[4] / "packages/contracts/openapi/ingestion-service.yaml"


def contrato() -> dict:
    return yaml.safe_load(CONTRATO.read_text(encoding="utf-8"))


def test_contract_declares_every_published_path(client: TestClient) -> None:
    publicado = client.get("/openapi.json").json()

    assert set(contrato()["paths"]) == set(publicado["paths"])


def test_each_published_operation_matches_the_contract(client: TestClient) -> None:
    publicado = client.get("/openapi.json").json()
    declarado = contrato()["paths"]

    for caminho, operacoes in publicado["paths"].items():
        assert declarado[caminho] == operacoes, f"contrato desatualizado em {caminho}"


def test_each_published_schema_matches_the_contract(client: TestClient) -> None:
    publicado = client.get("/openapi.json").json()
    declarado = contrato()["components"]["schemas"]

    for nome, schema in publicado["components"]["schemas"].items():
        assert declarado[nome] == schema, f"schema desatualizado: {nome}"


def test_capture_route_is_part_of_the_contract() -> None:
    """A porta de entrada do RF09 e o caminho que a equipe consome primeiro."""

    assert "post" in contrato()["paths"]["/api/v1/ingestion"]
