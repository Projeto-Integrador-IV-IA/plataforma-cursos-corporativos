"""Aceite RF09 na porta de entrada: captar e confirmar so depois do commit remoto.

A fronteira dublada e o ``PipelineClient``, nao o ``fetch``: e ali que mora o
contrato entre os dois microsservicos. O teste verifica tanto o caminho feliz
quanto a regra que da nome ao requisito - se a persistencia nao confirmou, a
captacao nao pode ser anunciada como recebida.
"""

from collections.abc import Iterator
from datetime import UTC, datetime
from uuid import UUID, uuid4

import pytest
from fastapi.testclient import TestClient

from app.api.v1.routes.ingestion import get_pipeline_client
from app.core.exceptions import UpstreamError
from app.domain.raw_demand import PersistedRawDemand, RawDemand, SourceKind
from app.main import create_app

TEXTO = "Oi! Queremos formar 25 tecnicos na NR-12 ate marco.\n-- enviado do meu celular"


class PipelineDublado:
    """Registra o que recebeu para que o teste possa afirmar o que foi enviado."""

    def __init__(self, erro: Exception | None = None) -> None:
        self.erro = erro
        self.chamadas: list[tuple[RawDemand, UUID]] = []

    def persist_raw_demand(
        self,
        raw_demand: RawDemand,
        *,
        author_id: UUID,
        request_id: str | None = None,
    ) -> PersistedRawDemand:
        self.chamadas.append((raw_demand, author_id))
        if self.erro is not None:
            raise self.erro
        return PersistedRawDemand(
            raw_input_id=uuid4(),
            demand_id=raw_demand.demand_id,
            source_type=raw_demand.source_type,
            created_at=datetime.now(UTC),
        )


@pytest.fixture
def pipeline() -> PipelineDublado:
    return PipelineDublado()


@pytest.fixture
def api(pipeline: PipelineDublado) -> Iterator[TestClient]:
    application = create_app()
    application.dependency_overrides[get_pipeline_client] = lambda: pipeline
    with TestClient(application) as client:
        yield client


def captar(api: TestClient, *, text: str = TEXTO, source: str = "MENSAGENS", **extra):
    corpo = {"text": text, "source_type": source, "demand_id": str(uuid4()), **extra}
    return api.post("/api/v1/ingestion", json=corpo, headers={"X-User-ID": str(uuid4())})


def test_capture_is_confirmed_only_after_the_pipeline_commits(
    api: TestClient, pipeline: PipelineDublado
) -> None:
    resposta = captar(api)

    assert resposta.status_code == 201, resposta.text
    corpo = resposta.json()
    assert corpo["status"] == "RECEBIDA"
    assert UUID(corpo["raw_input_id"])
    assert len(pipeline.chamadas) == 1


def test_the_text_handed_to_the_pipeline_is_the_one_the_operator_pasted(
    api: TestClient, pipeline: PipelineDublado
) -> None:
    """Nenhuma sanitizacao na captacao: o RF11 acontece depois, em campo separado."""

    captar(api)

    recebido, _ = pipeline.chamadas[0]
    assert recebido.text == TEXTO
    assert recebido.source_type is SourceKind.MENSAGENS


@pytest.mark.parametrize(
    ("status", "code"),
    [(404, "DEMAND_NOT_FOUND"), (504, "PIPELINE_TIMEOUT"), (502, "PIPELINE_UNAVAILABLE")],
)
def test_failure_to_persist_is_reported_and_not_swallowed(status: int, code: str) -> None:
    """Sem confirmacao do pipeline nao ha captacao - e o operador fica sabendo."""

    pipeline = PipelineDublado(erro=UpstreamError(status_code=status, code=code, message="falhou"))
    application = create_app()
    application.dependency_overrides[get_pipeline_client] = lambda: pipeline
    with TestClient(application, raise_server_exceptions=False) as api:
        resposta = captar(api)

    assert resposta.status_code == status
    assert resposta.json()["error"]["code"] == code


@pytest.mark.parametrize("texto", ["", "   ", "\n\t "])
def test_blank_text_is_refused_without_touching_the_pipeline(
    api: TestClient, pipeline: PipelineDublado, texto: str
) -> None:
    assert captar(api, text=texto).status_code == 422
    assert pipeline.chamadas == []


def test_unknown_source_is_refused_without_touching_the_pipeline(
    api: TestClient, pipeline: PipelineDublado
) -> None:
    assert captar(api, source="POMBO_CORREIO").status_code == 422
    assert pipeline.chamadas == []


def test_unexpected_field_is_refused(api: TestClient, pipeline: PipelineDublado) -> None:
    assert captar(api, normalized_text="ja limpo").status_code == 422
    assert pipeline.chamadas == []


def test_capture_without_operator_header_is_refused(
    api: TestClient, pipeline: PipelineDublado
) -> None:
    resposta = api.post(
        "/api/v1/ingestion",
        json={"text": TEXTO, "source_type": "MENSAGENS", "demand_id": str(uuid4())},
    )

    assert resposta.status_code == 422
    assert pipeline.chamadas == []
