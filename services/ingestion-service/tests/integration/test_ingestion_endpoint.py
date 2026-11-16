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
from app.core.config import DEFAULT_SOURCE_TEXT_MAX_LENGTH
from app.core.exceptions import UpstreamError
from app.domain.raw_demand import PersistedRawDemand, RawDemand, SourceKind
from app.main import create_app
from app.schemas.ingestion import SOURCE_TEXT_MIN_CONTENT_LENGTH

TEXTO = "Oi! Queremos formar 25 tecnicos na NR-12 ate marco.\n-- enviado do meu celular"


class PipelineDublado:
    """Registra o que recebeu para que o teste possa afirmar o que foi enviado."""

    def __init__(
        self, erro: Exception | None = None, erro_na_sanitizacao: Exception | None = None
    ) -> None:
        self.erro = erro
        self.erro_na_sanitizacao = erro_na_sanitizacao
        self.chamadas: list[tuple[RawDemand, UUID]] = []
        self.sanitizacoes: list[tuple[UUID, str]] = []
        self.ordem: list[str] = []

    def persist_raw_demand(
        self,
        raw_demand: RawDemand,
        *,
        author_id: UUID,
        request_id: str | None = None,
    ) -> PersistedRawDemand:
        self.ordem.append("original")
        self.chamadas.append((raw_demand, author_id))
        if self.erro is not None:
            raise self.erro
        return PersistedRawDemand(
            raw_input_id=uuid4(),
            demand_id=raw_demand.demand_id,
            source_type=raw_demand.source_type,
            created_at=datetime.now(UTC),
        )

    def persist_normalization(
        self, raw_input_id: UUID, normalized_content: str, *, request_id: str | None = None
    ) -> None:
        self.ordem.append("sanitizado")
        self.sanitizacoes.append((raw_input_id, normalized_content))
        if self.erro_na_sanitizacao is not None:
            raise self.erro_na_sanitizacao


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


@pytest.mark.parametrize("source", [{}, {"source_type": None}])
def test_missing_or_null_source_is_inferred_before_persisting(
    api: TestClient, pipeline: PipelineDublado, source: dict[str, None]
) -> None:
    text = "De: marina@example.com\nAssunto: Curso\n\nPrecisamos de 20 vagas."
    operator = uuid4()
    response = api.post(
        "/api/v1/ingestion",
        json={"text": text, "demand_id": str(uuid4()), **source},
        headers={"X-User-ID": str(operator)},
    )

    assert response.status_code == 201, response.text
    assert response.json()["source_type"] == "EMAIL"
    raw, author = pipeline.chamadas[0]
    assert raw.text == text
    assert raw.source_type is SourceKind.EMAIL
    assert author == operator
    assert pipeline.ordem == ["original", "sanitizado"]
    assert pipeline.sanitizacoes[0][1] == "Precisamos de 20 vagas."


@pytest.mark.parametrize("source", list(SourceKind))
def test_operator_choice_overrides_inference(
    api: TestClient, pipeline: PipelineDublado, source: SourceKind
) -> None:
    text = "From: marina@example.com\nSubject: Curso\n\nPrecisamos de 20 vagas."
    response = captar(api, text=text, source=source.value)

    assert response.status_code == 201, response.text
    assert response.json()["source_type"] == source.value
    assert pipeline.chamadas[0][0].source_type is source
    assert pipeline.chamadas[0][0].text == text


def test_ambiguous_source_is_recorded_as_other(api: TestClient, pipeline: PipelineDublado) -> None:
    response = api.post(
        "/api/v1/ingestion",
        json={"text": TEXTO, "demand_id": str(uuid4())},
        headers={"X-User-ID": str(uuid4())},
    )

    assert response.status_code == 201, response.text
    assert response.json()["source_type"] == "OUTRO"
    assert pipeline.chamadas[0][0].text == TEXTO


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


@pytest.mark.parametrize(
    ("text", "issue_type", "message_part"),
    [
        ("", "source_text_too_short", "pelo menos 10 caracteres nao brancos"),
        ("   \n\t ", "source_text_too_short", "pelo menos 10 caracteres nao brancos"),
        ("curso", "source_text_too_short", "pelo menos 10 caracteres nao brancos"),
        (123, "source_text_invalid_format", "deve ser enviado como texto"),
        (
            "a" * (DEFAULT_SOURCE_TEXT_MAX_LENGTH + 1),
            "source_text_too_long",
            "no maximo 50000 caracteres",
        ),
    ],
    ids=["empty", "whitespace", "too-short", "not-text", "too-long"],
)
def test_invalid_text_is_described_and_refused_without_touching_the_pipeline(
    api: TestClient,
    pipeline: PipelineDublado,
    text: object,
    issue_type: str,
    message_part: str,
) -> None:
    response = captar(api, text=text)

    assert response.status_code == 422
    assert response.json()["error"]["code"] == "VALIDATION_ERROR"
    assert response.json()["error"]["message"] == "A fonte recebida e invalida."
    issue = response.json()["error"]["details"]["issues"][0]
    assert issue["location"] == ["body", "text"]
    assert issue["type"] == issue_type
    assert message_part in issue["message"]
    assert pipeline.chamadas == []


@pytest.mark.parametrize("source", ["POMBO_CORREIO", ""])
def test_unknown_source_is_refused_without_touching_the_pipeline(
    api: TestClient, pipeline: PipelineDublado, source: str
) -> None:
    response = captar(api, source=source)

    assert response.status_code == 422
    issue = response.json()["error"]["details"]["issues"][0]
    assert issue == {
        "location": ["body", "source_type"],
        "message": (
            "O formato da fonte e invalido. Use um de: "
            "EMAIL, TRANSCRICAO, MENSAGENS, ANOTACAO, OUTRO."
        ),
        "type": "source_type_invalid",
    }
    assert pipeline.chamadas == []


@pytest.mark.parametrize(
    "text",
    [
        " " + ("a" * SOURCE_TEXT_MIN_CONTENT_LENGTH) + "\n",
        "a" * DEFAULT_SOURCE_TEXT_MAX_LENGTH,
    ],
    ids=["minimum-content", "maximum-size"],
)
def test_boundary_source_text_is_preserved_exactly(
    api: TestClient, pipeline: PipelineDublado, text: str
) -> None:
    response = captar(api, text=text)

    assert response.status_code == 201, response.text
    assert pipeline.chamadas[0][0].text == text


@pytest.mark.parametrize("limit", [10, 100, 60_000])
def test_environment_limit_controls_capture_and_openapi(
    monkeypatch: pytest.MonkeyPatch,
    api: TestClient,
    pipeline: PipelineDublado,
    limit: int,
) -> None:
    monkeypatch.setenv("SOURCE_TEXT_MAX_LENGTH", str(limit))
    text = "á" * limit if limit == 10 else "á" * (limit - 1) + "\n"
    accepted = captar(api, text=text)
    assert accepted.status_code == 201, accepted.text
    assert pipeline.chamadas[0][0].text == text

    rejected = api.post(
        "/api/v1/ingestion",
        json={"text": text + "x", "demand_id": str(uuid4())},
        headers={"X-User-ID": str(uuid4()), "X-Request-ID": "rnf13-limit"},
    )
    assert rejected.status_code == 422
    error = rejected.json()["error"]
    assert error["code"] == "VALIDATION_ERROR"
    assert error["request_id"] == "rnf13-limit"
    assert error["details"]["issues"] == [
        {
            "location": ["body", "text"],
            "type": "source_text_too_long",
            "message": f"A fonte deve conter no maximo {limit} caracteres.",
        }
    ]
    assert len(pipeline.chamadas) == 1
    assert len(pipeline.sanitizacoes) == 1
    schema = api.get("/openapi.json").json()["components"]["schemas"]["IngestionCreate"]
    assert schema["properties"]["text"]["maxLength"] == limit


def test_oversized_whitespace_is_rejected_by_size_first(
    monkeypatch: pytest.MonkeyPatch, api: TestClient, pipeline: PipelineDublado
) -> None:
    monkeypatch.setenv("SOURCE_TEXT_MAX_LENGTH", "10")
    response = captar(api, text=" " * 11)
    assert response.status_code == 422
    assert response.json()["error"]["details"]["issues"][0]["type"] == "source_text_too_long"
    assert pipeline.chamadas == []


def test_validation_error_keeps_request_correlation(
    api: TestClient, pipeline: PipelineDublado
) -> None:
    response = api.post(
        "/api/v1/ingestion",
        json={"text": "curto", "source_type": "OUTRO", "demand_id": str(uuid4())},
        headers={"X-User-ID": str(uuid4()), "X-Request-ID": "rf12-invalid-source"},
    )

    assert response.status_code == 422
    assert response.json()["error"]["request_id"] == "rf12-invalid-source"
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


def test_the_original_is_persisted_before_the_sanitized_copy(
    api: TestClient, pipeline: PipelineDublado
) -> None:
    """A ordem e o requisito: sanitizar antes de gravar arriscaria perder o bruto."""

    captar(api)

    assert pipeline.ordem == ["original", "sanitizado"]


def test_the_sanitized_copy_goes_to_the_record_just_created(
    api: TestClient, pipeline: PipelineDublado
) -> None:
    resposta = captar(api)

    raw_input_id, conteudo = pipeline.sanitizacoes[0]
    assert str(raw_input_id) == resposta.json()["raw_input_id"]
    assert conteudo != ""


def test_failure_to_save_the_sanitized_copy_does_not_lose_the_capture() -> None:
    """Criterio de aceite do #30: falha em etapa seguinte nao derruba o bruto.

    Responder erro aqui faria o operador colar o texto outra vez e duplicar a
    fonte, justamente o oposto do que o requisito protege. A captacao confirma,
    e o registro fica com ``normalized_content`` nulo para o reprocessamento.
    """

    pipeline = PipelineDublado(
        erro_na_sanitizacao=UpstreamError(
            status_code=504, code="PIPELINE_TIMEOUT", message="demorou"
        )
    )
    application = create_app()
    application.dependency_overrides[get_pipeline_client] = lambda: pipeline
    with TestClient(application, raise_server_exceptions=False) as api:
        resposta = captar(api)

    assert resposta.status_code == 201
    assert resposta.json()["status"] == "RECEBIDA"
    assert len(pipeline.chamadas) == 1


def test_failure_to_save_the_sanitized_copy_is_logged_without_client_text(
    caplog: pytest.LogCaptureFixture,
) -> None:
    """O alerta precisa achar o registro depois, sem vazar o texto do cliente (RNF11)."""

    pipeline = PipelineDublado(
        erro_na_sanitizacao=UpstreamError(
            status_code=502, code="PIPELINE_UNAVAILABLE", message="fora do ar"
        )
    )
    application = create_app()
    application.dependency_overrides[get_pipeline_client] = lambda: pipeline
    with (
        caplog.at_level("WARNING"),
        TestClient(application, raise_server_exceptions=False) as api,
    ):
        resposta = captar(api)

    registro = chr(10).join(caplog.messages)
    assert "PIPELINE_UNAVAILABLE" in registro
    assert resposta.json()["raw_input_id"] in registro
    assert TEXTO not in registro
