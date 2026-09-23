"""Contrato do ingestion-service com o pipeline-service na captacao (RF09).

O cliente e dublado por transporte do proprio httpx: o teste exercita o codigo
real de montagem da requisicao e de leitura da resposta, sem subir o outro
microsservico e sem substituir o metodo que esta sendo verificado.
"""

import json
from datetime import UTC, datetime
from uuid import uuid4

import httpx
import pytest

from app.clients.pipeline_client import PipelineClient
from app.core.exceptions import UpstreamError
from app.domain.raw_demand import RawDemand, SourceKind

TEXTO = "Precisamos treinar 25 tecnicos na NR-12.\n\nAbs,\nMarina"


def demanda_bruta(text: str = TEXTO) -> RawDemand:
    return RawDemand(demand_id=uuid4(), text=text, source_type=SourceKind.MENSAGENS)


def cliente_com(handler) -> PipelineClient:
    transporte = httpx.MockTransport(handler)
    return PipelineClient(httpx.Client(transport=transporte, base_url="http://pipeline-service"))


def resposta_de_criacao(raw_demand: RawDemand) -> httpx.Response:
    return httpx.Response(
        201,
        json={
            "id": str(uuid4()),
            "demand_id": str(raw_demand.demand_id),
            "original_content": raw_demand.text,
            "source": raw_demand.source_type.value,
            "author_id": str(uuid4()),
            "created_at": datetime.now(UTC).isoformat(),
        },
    )


def test_original_text_reaches_the_pipeline_untouched() -> None:
    """O coracao do RF09: o que sai daqui e o que o operador colou, byte a byte."""

    raw_demand = demanda_bruta()
    enviado: dict[str, object] = {}

    def handler(request: httpx.Request) -> httpx.Response:
        enviado["url"] = str(request.url)
        enviado["json"] = json.loads(request.content)
        return resposta_de_criacao(raw_demand)

    cliente_com(handler).persist_raw_demand(raw_demand, author_id=uuid4())

    assert enviado["json"] == {"original_content": TEXTO, "source": "MENSAGENS"}
    assert str(raw_demand.demand_id) in str(enviado["url"])
    assert "raw-inputs" in str(enviado["url"])


def test_operator_and_request_travel_in_the_headers() -> None:
    raw_demand = demanda_bruta()
    author_id = uuid4()
    capturado: dict[str, str] = {}

    def handler(request: httpx.Request) -> httpx.Response:
        capturado.update(request.headers)
        return resposta_de_criacao(raw_demand)

    cliente_com(handler).persist_raw_demand(raw_demand, author_id=author_id, request_id="req-42")

    assert capturado["x-user-id"] == str(author_id)
    assert capturado["x-request-id"] == "req-42"


def test_confirmation_carries_the_identifier_given_by_the_pipeline() -> None:
    raw_demand = demanda_bruta()
    resposta = resposta_de_criacao(raw_demand)

    persistido = cliente_com(lambda _: resposta).persist_raw_demand(raw_demand, author_id=uuid4())

    assert str(persistido.raw_input_id) == resposta.json()["id"]
    assert persistido.demand_id == raw_demand.demand_id
    assert persistido.source_type is SourceKind.MENSAGENS


def test_timeout_becomes_gateway_timeout() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        raise httpx.ReadTimeout("demorou", request=request)

    with pytest.raises(UpstreamError) as erro:
        cliente_com(handler).persist_raw_demand(demanda_bruta(), author_id=uuid4())

    assert erro.value.status_code == 504
    assert erro.value.code == "PIPELINE_TIMEOUT"


def test_connection_failure_becomes_bad_gateway() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        raise httpx.ConnectError("recusou", request=request)

    with pytest.raises(UpstreamError) as erro:
        cliente_com(handler).persist_raw_demand(demanda_bruta(), author_id=uuid4())

    assert erro.value.status_code == 502
    assert erro.value.code == "PIPELINE_UNAVAILABLE"


@pytest.mark.parametrize("status", [404, 409, 422])
def test_client_errors_keep_their_meaning(status: int) -> None:
    """404 do pipeline nao vira 502: quem chamou precisa saber que a demanda nao existe."""

    corpo = {"error": {"code": "DEMAND_NOT_FOUND", "message": "Demanda nao encontrada."}}

    with pytest.raises(UpstreamError) as erro:
        cliente_com(lambda _: httpx.Response(status, json=corpo)).persist_raw_demand(
            demanda_bruta(), author_id=uuid4()
        )

    assert erro.value.status_code == status
    assert erro.value.code == "DEMAND_NOT_FOUND"


def test_server_error_is_reported_as_bad_gateway() -> None:
    corpo = {"error": {"code": "INTERNAL_ERROR", "message": "falhou"}}

    with pytest.raises(UpstreamError) as erro:
        cliente_com(lambda _: httpx.Response(500, json=corpo)).persist_raw_demand(
            demanda_bruta(), author_id=uuid4()
        )

    assert erro.value.status_code == 502


def test_unreadable_response_does_not_pass_as_success() -> None:
    """Resposta fora do envelope e falha declarada, nao captacao silenciosa."""

    with pytest.raises(UpstreamError) as erro:
        cliente_com(
            lambda _: httpx.Response(500, text="<html>Bad Gateway</html>")
        ).persist_raw_demand(demanda_bruta(), author_id=uuid4())

    assert erro.value.code == "PIPELINE_INVALID_RESPONSE"


def test_blank_text_never_reaches_the_pipeline() -> None:
    """A recusa acontece no dominio, antes de gastar uma chamada de rede."""

    with pytest.raises(ValueError):
        demanda_bruta("   \n\t ")
