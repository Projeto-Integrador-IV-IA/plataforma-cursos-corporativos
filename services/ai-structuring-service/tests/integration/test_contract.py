"""O contrato publicado do ai-structuring-service acompanha o codigo (RNF02).

Sem esta verificacao o arquivo em ``packages/contracts`` vira documentacao
optativa: ele ficou como ``paths: {}`` enquanto o servico ja tinha rota.
"""

from pathlib import Path

import yaml
from fastapi.testclient import TestClient

CONTRATO = (
    Path(__file__).resolve().parents[4] / "packages/contracts/openapi/ai-structuring-service.yaml"
)


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


def test_both_structuring_paths_are_part_of_the_contract() -> None:
    """Os dois caminhos sao contrato: o sincrono e usado pela avaliacao (RNF04),
    e o assincrono pela interface (RF17)."""

    caminhos = contrato()["paths"]
    assert "post" in caminhos["/api/v1/structuring"]
    assert "post" in caminhos["/api/v1/structuring/jobs"]
    assert "get" in caminhos["/api/v1/structuring/jobs/{job_id}"]
