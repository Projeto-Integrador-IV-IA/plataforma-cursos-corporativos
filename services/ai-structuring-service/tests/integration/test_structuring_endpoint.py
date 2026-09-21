"""Caso de uso da estruturacao exercitado pela rota HTTP (RF11, RF12).

RF11 na matriz de rastreabilidade; **RF13.1** no Documento Consolidado de
Requisitos v1.0.

O que estes testes protegem: ``POST /api/v1/structuring`` recebe o texto ja
normalizado e devolve tema, publico, carga horaria, ementa e objetivos na forma
canonica - ou um erro que diz o que aconteceu, sem perder a demanda bruta.

E o caminho inteiro, do corpo da requisicao ate a resposta: prompt versionado,
provedor, validacao de schema e traducao do desfecho. O provedor e sempre o
mock ou um duble sobre ele - nenhum teste toca rede, chave ou custo (RNF12).
"""

from collections.abc import Callable, Iterator

import pytest
from fastapi.testclient import TestClient

from app.api.v1.routes.structuring import get_structuring_service
from app.core.config import Settings, get_settings
from app.core.exceptions import LLMProviderError, LLMTimeoutError, LLMUnavailableError
from app.domain.course import CHAVES_CANONICAS
from app.main import create_app
from app.providers import CompletionParams, CompletionResult, MockLLMProvider
from app.services.structuring_service import StructuringService
from tests.conftest import MakeSettings

ROTA = "/api/v1/structuring"

EMAIL_COLADO = """
De: [contato do cliente]
Assunto: ENC: treinamento pra equipe de manutencao

Boa tarde, tudo bem?

Conforme conversamos, precisamos de um treinamento de NR-12 para o pessoal da manutencao da
planta 2, uns 25 tecnicos. A ideia e fazer em dois dias de 8 horas, no proprio site.
"""

CINCO_CAMPOS = ("tema", "publico_alvo", "carga_horaria", "ementa", "objetivos_aprendizagem")

DEMANDA = {"demand_id": "dem-2026-0042", "text": EMAIL_COLADO}

MontarCliente = Callable[..., TestClient]


class _ProviderEspiao(MockLLMProvider):
    """Mock que guarda o que foi enviado, para conferir o prompt montado."""

    def __init__(self, **kwargs: object) -> None:
        super().__init__(**kwargs)  # type: ignore[arg-type]
        self.chamadas: list[tuple[str, CompletionParams | None]] = []

    async def complete(
        self,
        prompt: str,
        params: CompletionParams | None = None,
    ) -> CompletionResult:
        self.chamadas.append((prompt, params))
        return await super().complete(prompt, params)


@pytest.fixture
def montar_cliente(make_settings: MakeSettings) -> Iterator[MontarCliente]:
    """Sobe a aplicacao com configuracao de teste e, se pedido, outro provedor.

    Sem isto o servico leria o ambiente real na primeira requisicao: o que se
    quer testar e a rota, nao o `.env` da maquina (RNF11).
    """

    aplicacao = create_app()

    def _montar(provider: object | None = None, **overrides: object) -> TestClient:
        settings: Settings = make_settings(**overrides)
        aplicacao.dependency_overrides[get_settings] = lambda: settings
        if provider is not None:
            aplicacao.dependency_overrides[get_structuring_service] = (
                lambda: StructuringService(provider, settings, sleep=_nao_dormir)  # type: ignore[arg-type]
            )
        return TestClient(aplicacao)

    yield _montar
    aplicacao.dependency_overrides.clear()


async def _nao_dormir(segundos: float) -> None:
    """Espera de mentira: a politica de retentativa nao atrasa o teste."""


# ----------------------------------------------------------------------
# Criterio de aceite: os cinco campos, pelo provedor mock
# ----------------------------------------------------------------------


def test_endpoint_devolve_os_cinco_campos(montar_cliente: MontarCliente) -> None:
    """Criterio de aceite: tema, publico, carga horaria, ementa e objetivos."""

    with montar_cliente() as client:
        resposta = client.post(ROTA, json=DEMANDA)

    assert resposta.status_code == 200
    curso = resposta.json()["course"]
    for campo in CINCO_CAMPOS:
        assert campo in curso, f"campo {campo} ausente na saida"
    assert curso["tema"]
    assert curso["publico_alvo"]
    assert curso["carga_horaria"]
    assert curso["ementa"]
    assert curso["objetivos_aprendizagem"]


def test_resposta_segue_a_forma_canonica_do_curso(montar_cliente: MontarCliente) -> None:
    """A saida da rota e a mesma do dominio: mesmas chaves, mesma ordem (RNF03)."""

    with montar_cliente() as client:
        corpo = client.post(ROTA, json=DEMANDA).json()

    assert tuple(corpo["course"]) == CHAVES_CANONICAS
    assert corpo["demand_id"] == "dem-2026-0042"


def test_resposta_carrega_a_proveniencia_da_execucao(montar_cliente: MontarCliente) -> None:
    """Provedor, modelo, versao de prompt, tokens e tempo (RNF04, RNF06, RNF12)."""

    with montar_cliente() as client:
        execucao = client.post(ROTA, json=DEMANDA).json()["execution"]

    assert execucao["provider"] == "mock"
    assert execucao["model"] == "mock"
    assert execucao["prompt"] == "extract-requirements.v3"
    assert execucao["attempts"] == 1
    assert execucao["total_tokens"] == execucao["prompt_tokens"] + execucao["completion_tokens"]
    assert execucao["total_tokens"] > 0
    assert execucao["elapsed_ms"] >= 0


def test_texto_da_demanda_chega_integro_dentro_do_prompt_versionado(
    montar_cliente: MontarCliente,
) -> None:
    """O caso de uso monta o prompt; nao manda o texto cru nem trunca o colado."""

    provider = _ProviderEspiao()

    with montar_cliente(provider) as client:
        assert client.post(ROTA, json=DEMANDA).status_code == 200

    enviado, params = provider.chamadas[0]
    assert EMAIL_COLADO.strip() in enviado
    assert "Nunca invente" in enviado
    assert params is not None
    assert params.response_schema is not None
    assert params.temperature == 0.2
    assert params.timeout_seconds == 30.0


# ----------------------------------------------------------------------
# Criterio de aceite: o endpoint documentado no Swagger
# ----------------------------------------------------------------------


def test_endpoint_aparece_no_swagger_com_exemplo_de_requisicao_e_resposta(
    montar_cliente: MontarCliente,
) -> None:
    """Criterio de aceite: a demonstracao da pre-banca acontece no Swagger."""

    with montar_cliente() as client:
        openapi = client.get("/openapi.json").json()

    operacao = openapi["paths"][ROTA]["post"]
    schemas = openapi["components"]["schemas"]

    requisicao = operacao["requestBody"]["content"]["application/json"]["schema"]["$ref"]
    resposta = operacao["responses"]["200"]["content"]["application/json"]["schema"]["$ref"]

    assert schemas[requisicao.rsplit("/", 1)[-1]]["examples"]
    assert schemas[resposta.rsplit("/", 1)[-1]]["examples"]
    assert set(operacao["responses"]) >= {"200", "422", "502", "503", "504"}


# ----------------------------------------------------------------------
# Falha: erro identificado, demanda preservada
# ----------------------------------------------------------------------


@pytest.mark.parametrize(
    ("falha", "status", "code"),
    [
        (LLMTimeoutError(timeout_seconds=15.0), 504, "LLM_TIMEOUT"),
        (LLMUnavailableError(), 503, "LLM_UNAVAILABLE"),
    ],
)
def test_falha_do_provedor_vira_erro_identificado(
    montar_cliente: MontarCliente,
    falha: LLMProviderError,
    status: int,
    code: str,
) -> None:
    """Falha do fornecedor nao chega ao operador como 500 generico (RNF02, RNF05)."""

    with montar_cliente(MockLLMProvider(fail_with=falha), llm_max_retries=0) as client:
        resposta = client.post(
            ROTA,
            json=DEMANDA,
            headers={"X-Request-ID": "req-2026-0042"},
        )

    erro = resposta.json()["error"]
    assert resposta.status_code == status
    assert erro["code"] == code
    assert erro["request_id"] == "req-2026-0042"
    assert erro["details"]["demand_id"] == "dem-2026-0042"
    assert erro["details"]["retryable"] is True


def test_resposta_fora_do_schema_e_recusada_e_nao_devolve_curso_pela_metade(
    montar_cliente: MontarCliente,
) -> None:
    """Resposta "quase certa" e falha, nao resultado aproveitavel (ADR-0006)."""

    provider = MockLLMProvider(response_text='{"tema": "NR-12", "sobrando": true}')

    with montar_cliente(provider, llm_max_retries=2) as client:
        resposta = client.post(ROTA, json=DEMANDA)

    erro = resposta.json()["error"]
    assert resposta.status_code == 502
    assert erro["code"] == "LLM_INVALID_RESPONSE"
    assert erro["details"]["prompt"] == "extract-requirements.v3"
    assert erro["details"]["retryable"] is False
    assert erro["details"]["violacoes"]
    assert "course" not in resposta.json()


def test_texto_do_cliente_nao_vaza_no_corpo_de_erro(montar_cliente: MontarCliente) -> None:
    """RNF10: o corpo de erro identifica a demanda, nao repete o que ela diz."""

    provider = MockLLMProvider(response_text="isto nao e json")

    with montar_cliente(provider, llm_max_retries=0) as client:
        resposta = client.post(ROTA, json=DEMANDA)

    assert resposta.status_code == 502
    assert "NR-12" not in resposta.text


# ----------------------------------------------------------------------
# Entrada invalida barrada na fronteira
# ----------------------------------------------------------------------


@pytest.mark.parametrize(
    ("rotulo", "corpo"),
    [
        ("sem texto", {"demand_id": "dem-1", "text": ""}),
        ("sem identificador", {"demand_id": "", "text": EMAIL_COLADO}),
        ("campo desconhecido", {**DEMANDA, "cliente": "Metalurgica Exemplo"}),
        ("versao de prompt inexistente", {**DEMANDA, "prompt_version": "v9"}),
    ],
)
def test_entrada_invalida_e_recusada_antes_de_chamar_o_provedor(
    montar_cliente: MontarCliente,
    rotulo: str,
    corpo: dict[str, object],
) -> None:
    provider = _ProviderEspiao()

    with montar_cliente(provider) as client:
        resposta = client.post(ROTA, json=corpo)

    assert resposta.status_code == 422, rotulo
    assert provider.chamadas == [], rotulo


def test_exemplo_do_swagger_obedece_ao_dominio() -> None:
    """O exemplo da documentacao tem de ser uma resposta que o dominio aceita.

    Sem esta trava o exemplo envelhece calado: ele nao passa por validacao em
    nenhum outro lugar, e foi assim que ficou com a forma antiga de
    ``campos_ausentes`` depois que o dominio mudou.
    """

    from app.domain.course import StructuredCourse
    from app.prompts import carregar_prompt
    from app.schemas.structuring import EXEMPLO_DE_REQUISICAO, EXEMPLO_DE_RESPOSTA
    from app.services.structuring_service import DEFAULT_PROMPT_VERSION, EXTRACTION_PROMPT_NAME

    curso = StructuredCourse.model_validate(EXEMPLO_DE_RESPOSTA["course"])
    assert list(curso.to_canonical_dict()) == list(EXEMPLO_DE_RESPOSTA["course"])

    prompt_do_exemplo = EXEMPLO_DE_RESPOSTA["execution"]["prompt"]
    assert prompt_do_exemplo == f"{EXTRACTION_PROMPT_NAME}.{DEFAULT_PROMPT_VERSION}"
    assert EXEMPLO_DE_REQUISICAO["prompt_version"] == DEFAULT_PROMPT_VERSION
    assert carregar_prompt(EXTRACTION_PROMPT_NAME, DEFAULT_PROMPT_VERSION).metadados["status"] == (
        "ativo"
    )
