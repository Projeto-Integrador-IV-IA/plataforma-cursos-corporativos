"""Aceite RF17/RNF06: a estruturacao nao prende quem chamou.

O pedido e aceito de imediato, com um identificador, e o estado e consultado
depois. O que estes testes protegem e o que a interface (#82) depende: que o
aceite nao espera o modelo, que o estado caminha ate um desfecho, e que o
identificador continua valendo entre requisicoes.

O provedor e sempre o mock ou um duble sobre ele - nenhum teste toca rede,
chave ou custo (RNF12).
"""

import asyncio
from collections.abc import Callable, Iterator
from uuid import uuid4

import pytest
from fastapi.testclient import TestClient

from app.api.v1.routes.structuring import get_structuring_service
from app.core.config import Settings, get_settings
from app.core.exceptions import LLMTimeoutError
from app.main import create_app
from app.providers import CompletionParams, CompletionResult, MockLLMProvider
from app.services.structuring_service import StructuringService
from tests.conftest import MakeSettings

ROTA_ACEITE = "/api/v1/structuring/jobs"
DEMANDA = {
    "demand_id": "dem-2026-0042",
    "text": (
        "Precisamos de um treinamento de NR-12 para 25 tecnicos da manutencao da planta 2, "
        "em dois dias de 8 horas, no proprio site."
    ),
}

MontarCliente = Callable[..., TestClient]


async def _nao_dormir(segundos: float) -> None:
    """Espera de mentira: a politica de retentativa nao atrasa o teste."""


class _ProvedorLento(MockLLMProvider):
    """Mock que so responde quando o teste liberar, para observar o estado no meio."""

    def __init__(self, **kwargs: object) -> None:
        super().__init__(**kwargs)  # type: ignore[arg-type]
        self.liberar = asyncio.Event()

    async def complete(
        self,
        prompt: str,
        params: CompletionParams | None = None,
    ) -> CompletionResult:
        await self.liberar.wait()
        return await super().complete(prompt, params)


class _ProvedorQueFalha(MockLLMProvider):
    """Mock que sempre estoura o tempo, para exercitar o desfecho de erro."""

    async def complete(
        self,
        prompt: str,
        params: CompletionParams | None = None,
    ) -> CompletionResult:
        raise LLMTimeoutError("o provedor demorou demais")


@pytest.fixture
def montar_cliente(make_settings: MakeSettings) -> Iterator[MontarCliente]:
    """Sobe a aplicacao com configuracao de teste e, se pedido, outro provedor."""

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


def aceitar(client: TestClient, **extra):
    return client.post(ROTA_ACEITE, json={**DEMANDA, **extra})


def consultar(client: TestClient, job_id: str):
    return client.get(f"{ROTA_ACEITE}/{job_id}")


#: Consultas ate desistir de esperar um desfecho. Nao ha ``sleep``: cada
#: requisicao ja devolve o controle ao laco de eventos, que e onde a execucao
#: roda.
TENTATIVAS_ATE_O_DESFECHO = 200


def aguardar_desfecho(client: TestClient, job_id: str) -> dict:
    """Consulta ate a execucao chegar a um estado final.

    Sem isto o teste dependeria de a tarefa em segundo plano terminar entre o
    aceite e a primeira consulta - o que costuma acontecer e nao esta
    garantido. Esperar o desfecho explicitamente e o que torna o resultado
    reproduzivel em vez de provavel.
    """

    for _ in range(TENTATIVAS_ATE_O_DESFECHO):
        corpo = consultar(client, job_id).json()
        if corpo["status"] in {"CONCLUIDA", "ERRO"}:
            return corpo
    raise AssertionError(
        f"a execucao {job_id} nao chegou a um desfecho em "
        f"{TENTATIVAS_ATE_O_DESFECHO} consultas; ultimo estado: {corpo['status']}"
    )


def test_pedido_e_aceito_com_identificador(montar_cliente: MontarCliente) -> None:
    """202 e nao 200: o que volta e a execucao, nao o curso, que ainda nao existe."""

    with montar_cliente() as client:
        resposta = aceitar(client)

    assert resposta.status_code == 202
    corpo = resposta.json()
    assert corpo["job_id"]
    assert corpo["demand_id"] == DEMANDA["demand_id"]
    assert corpo["status"] in {"PENDENTE", "PROCESSANDO", "CONCLUIDA"}


def test_execucao_chega_a_concluida_com_o_curso(montar_cliente: MontarCliente) -> None:
    with montar_cliente() as client:
        job_id = aceitar(client).json()["job_id"]
        corpo = aguardar_desfecho(client, job_id)

    assert corpo["status"] == "CONCLUIDA"
    assert corpo["result"]["course"]["tema"]
    assert corpo["result"]["demand_id"] == DEMANDA["demand_id"]


def test_identificador_continua_valendo_entre_requisicoes(
    montar_cliente: MontarCliente,
) -> None:
    """O registro vive na aplicacao, nao na requisicao.

    Se fosse criado por requisicao, o identificador devolvido no aceite
    responderia 404 na consulta seguinte - e a tela de acompanhamento nunca
    sairia do lugar.
    """

    with montar_cliente() as client:
        job_id = aceitar(client).json()["job_id"]

        assert consultar(client, job_id).status_code == 200
        assert consultar(client, job_id).status_code == 200
        assert consultar(client, job_id).json()["job_id"] == job_id


def test_execucoes_diferentes_nao_se_misturam(montar_cliente: MontarCliente) -> None:
    with montar_cliente() as client:
        primeiro = aceitar(client, demand_id="dem-0001").json()["job_id"]
        segundo = aceitar(client, demand_id="dem-0002").json()["job_id"]

        assert primeiro != segundo
        assert consultar(client, primeiro).json()["demand_id"] == "dem-0001"
        assert consultar(client, segundo).json()["demand_id"] == "dem-0002"


def test_estado_intermediario_nao_entrega_curso_pela_metade(
    montar_cliente: MontarCliente,
) -> None:
    """Enquanto nao concluiu, ``result`` e nulo - nao existe curso parcial (RNF03)."""

    provedor = _ProvedorLento(model="mock")
    with montar_cliente(provider=provedor) as client:
        job_id = aceitar(client).json()["job_id"]
        em_andamento = consultar(client, job_id).json()

        assert em_andamento["status"] in {"PENDENTE", "PROCESSANDO"}
        assert em_andamento["result"] is None
        assert em_andamento["finished_at"] is None
        assert em_andamento["error"] is None


def test_falha_do_provedor_encerra_a_execucao_com_erro(
    montar_cliente: MontarCliente,
) -> None:
    """Nenhuma falha pode deixar a execucao pendurada em PROCESSANDO para sempre."""

    with montar_cliente(provider=_ProvedorQueFalha(model="mock")) as client:
        job_id = aceitar(client).json()["job_id"]
        corpo = aguardar_desfecho(client, job_id)

    assert corpo["status"] == "ERRO"
    assert corpo["error"]["code"] == "LLM_TIMEOUT"
    assert corpo["result"] is None
    assert corpo["finished_at"] is not None


def test_execucao_concluida_relata_o_tempo_de_ponta_a_ponta(
    montar_cliente: MontarCliente,
) -> None:
    """O numero que se compara ao limite acordado inclui a espera na fila (RNF06)."""

    with montar_cliente() as client:
        job_id = aceitar(client).json()["job_id"]
        corpo = aguardar_desfecho(client, job_id)

    assert corpo["total_elapsed_ms"] is not None
    assert corpo["total_elapsed_ms"] >= 0
    assert corpo["execution"]["elapsed_ms"] >= 0
    assert corpo["execution"]["prompt"].startswith("extract-requirements.")


def test_identificador_desconhecido_e_recusado(montar_cliente: MontarCliente) -> None:
    with montar_cliente() as client:
        resposta = consultar(client, str(uuid4()))

    assert resposta.status_code == 404
    assert resposta.json()["error"]["code"] == "STRUCTURING_JOB_NOT_FOUND"


def test_identificador_fora_do_formato_e_recusado(montar_cliente: MontarCliente) -> None:
    with montar_cliente() as client:
        assert consultar(client, "nao-e-uuid").status_code == 422


@pytest.mark.parametrize(
    "invalido",
    [
        {"text": ""},
        {"text": "   "},
        {"demand_id": ""},
        {"prompt_version": "v999"},
    ],
)
def test_entrada_invalida_nao_ocupa_lugar_na_fila(
    montar_cliente: MontarCliente, invalido: dict
) -> None:
    """A validacao e a mesma do caminho sincrono: recusa antes de aceitar."""

    with montar_cliente() as client:
        assert aceitar(client, **invalido).status_code == 422


def test_campo_desconhecido_e_recusado(montar_cliente: MontarCliente) -> None:
    with montar_cliente() as client:
        assert aceitar(client, prioridade="alta").status_code == 422


def test_caminho_sincrono_continua_funcionando(montar_cliente: MontarCliente) -> None:
    """O assincrono acrescenta um caminho; nao substitui o que a avaliacao usa (RNF04)."""

    with montar_cliente() as client:
        resposta = client.post("/api/v1/structuring", json=DEMANDA)

    assert resposta.status_code == 200
    assert resposta.json()["course"]["tema"]
