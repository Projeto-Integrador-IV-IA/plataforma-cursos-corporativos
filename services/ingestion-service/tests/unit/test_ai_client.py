"""Contrato do adaptador entre as fontes normalizadas e a estruturacao (RF11)."""

import json
from pathlib import Path
from uuid import uuid4

import httpx
import pytest
import yaml
from jsonschema import Draft202012Validator
from pydantic import ValidationError

from app.clients.ai_client import AIClient
from app.core.exceptions import UpstreamError

CONTRACT = (
    Path(__file__).resolve().parents[4] / "packages/contracts/openapi/ai-structuring-service.yaml"
)


def client_with(handler) -> AIClient:
    transport = httpx.MockTransport(handler)
    return AIClient(httpx.Client(transport=transport, base_url="http://ai-structuring-service"))


def test_common_request_validates_against_structuring_contract() -> None:
    request = AIClient.build_request(
        uuid4(),
        ("Tema: LGPD", "Publico: gestores", "Carga horaria: 4 horas"),
    )
    contract = yaml.safe_load(CONTRACT.read_text(encoding="utf-8"))
    schema = contract["components"]["schemas"]["StructuringRequest"]

    Draft202012Validator(schema).validate(request.model_dump(mode="json"))


def test_multiple_sources_reach_ai_in_received_order() -> None:
    demand_id = uuid4()
    captured: dict[str, object] = {}

    def handler(request: httpx.Request) -> httpx.Response:
        captured["url"] = str(request.url)
        captured["json"] = json.loads(request.content)
        captured["request_id"] = request.headers.get("X-Request-ID")
        return httpx.Response(200, json={"demand_id": str(demand_id), "course": {}})

    response = client_with(handler).structure_course(
        demand_id,
        ("Primeira fonte", "Segunda fonte", "Terceira fonte"),
        source_ids=("fonte-1", "fonte-2", "fonte-3"),
        request_id="req-34",
    )

    assert captured["url"] == "http://ai-structuring-service/api/v1/structuring"
    assert captured["json"] == {
        "demand_id": str(demand_id),
        "text": "Primeira fonte\n\nSegunda fonte\n\nTerceira fonte",
        "source_ids": ["fonte-1", "fonte-2", "fonte-3"],
    }
    assert captured["request_id"] == "req-34"
    assert response["demand_id"] == str(demand_id)


def test_oversized_common_text_is_rejected_before_network_call() -> None:
    called = False

    def handler(_: httpx.Request) -> httpx.Response:
        nonlocal called
        called = True
        return httpx.Response(200, json={})

    with pytest.raises(ValidationError):
        client_with(handler).structure_course(uuid4(), ("a" * 50_001,))

    assert called is False


def test_timeout_is_reported_as_recoverable_upstream_failure() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        raise httpx.ReadTimeout("demorou", request=request)

    with pytest.raises(UpstreamError) as error:
        client_with(handler).structure_course(uuid4(), ("Tema: LGPD",))

    assert error.value.status_code == 504
    assert error.value.code == "AI_STRUCTURING_TIMEOUT"
