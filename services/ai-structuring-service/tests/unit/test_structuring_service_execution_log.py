"""Registro de execucao recuperavel por chamada ao provedor (RNF08.1).

RNF08 na matriz de rastreabilidade; **RNF08.1** no card #16.

O que estes testes protegem: toda chamada ao provedor - com sucesso ou com
falha esgotando as retentativas - produz um registro completo (modelo, versao
do prompt, parametros, tentativas, tokens, latencia) recuperavel por
``consultar_registros_de_execucao`` a partir do ``execution_id`` que o proprio
desfecho devolve. Sem isto, uma falha nunca deixava rastro - so o caminho de
sucesso tinha log, e nenhum dos dois era recuperavel por identificador.

O provedor e sempre o mock ou um duble programado. Nenhum teste toca rede,
chave ou custo (RNF12), e nenhum deixa o texto da demanda escapar para o
registro de log (RNF10) - e exatamente o tipo de vazamento que ``extra=``
convida, por isso ha um teste dedicado a provar que nao acontece.
"""

import json
from collections.abc import Callable
from uuid import uuid4

import pytest

from app.core.exceptions import LLMProviderError, LLMUnavailableError
from app.core.logging import configure_logging, consultar_registros_de_execucao
from app.providers import CompletionParams, CompletionResult, LLMProvider, MockLLMProvider
from app.services.structuring_service import RawDemand, StructuringService
from tests.conftest import MakeSettings

TEXTO_COLADO = (
    "Precisamos de um treinamento de NR-12 para 25 tecnicos da manutencao da "
    "planta 2 da Metalurgica Aurora, em dois dias de 8 horas."
)

DEMANDA = RawDemand(demand_id="dem-2026-0099", text=TEXTO_COLADO)

#: Termos do texto do cliente que nunca podem aparecer no registro recuperavel.
TERMOS_DO_CLIENTE = ("NR-12", "Metalurgica Aurora", "planta 2")

MontarServico = Callable[..., StructuringService]


class _ProviderQueSempreFalha(LLMProvider):
    """Provedor dublado que esgota toda tentativa com a mesma falha tipada."""

    name = "programado"

    def __init__(self, falha: LLMProviderError) -> None:
        self._falha = falha

    async def complete(
        self,
        prompt: str,
        params: CompletionParams | None = None,
    ) -> CompletionResult:
        raise self._falha


async def _nao_dormir(segundos: float) -> None:
    """Espera de mentira: a politica de retentativa nao atrasa o teste."""


@pytest.fixture(autouse=True)
def _log_estruturado_ligado() -> None:
    """Garante o handler de execucao no logger raiz, independente da ordem dos testes."""

    configure_logging("INFO")


@pytest.fixture
def montar_servico(make_settings: MakeSettings) -> MontarServico:
    def _montar(provider: LLMProvider, **overrides: object) -> StructuringService:
        base: dict[str, object] = {"llm_max_retries": 0, "llm_model": "vendor/modelo:free"}
        base.update(overrides)
        return StructuringService(provider, make_settings(**base), sleep=_nao_dormir)

    return _montar


# ----------------------------------------------------------------------
# Caminho de sucesso: registro completo e recuperavel
# ----------------------------------------------------------------------


async def test_chamada_bem_sucedida_fica_recuperavel_pelo_execution_id(
    montar_servico: MontarServico,
) -> None:
    servico = montar_servico(MockLLMProvider())

    outcome = await servico.structure_course(DEMANDA)

    assert outcome.succeeded
    registros = consultar_registros_de_execucao(outcome.execution_id)
    assert len(registros) == 1
    registro = registros[0]

    assert registro["nivel"] == "INFO"
    assert registro["execution_id"] == str(outcome.execution_id)
    assert registro["demand_id"] == "dem-2026-0099"
    assert registro["provider"] == "mock"
    assert registro["model"] == "vendor/modelo:free"
    assert registro["prompt_version"] == outcome.prompt_id
    assert registro["tentativas"] == 1
    assert registro["tokens_entrada"] == outcome.completion.usage.prompt_tokens
    assert registro["tokens_saida"] == outcome.completion.usage.completion_tokens
    assert registro["parametros_modelo"] == "vendor/modelo:free"
    assert registro["parametros_temperatura"] == pytest.approx(0.2)
    assert registro["duration_ms"] >= 0


async def test_structure_sem_passar_por_structure_course_tambem_fica_recuperavel(
    montar_servico: MontarServico,
) -> None:
    """``structure`` isolado (sem prompt versionado) ja gera registro recuperavel."""

    servico = montar_servico(MockLLMProvider())

    outcome = await servico.structure(DEMANDA)

    registros = consultar_registros_de_execucao(outcome.execution_id)
    assert len(registros) == 1
    assert "prompt_version" not in registros[0]


async def test_execution_id_informado_pelo_chamador_e_o_mesmo_no_desfecho(
    montar_servico: MontarServico,
) -> None:
    """O identificador nao muda: o chamador consulta pelo que ele proprio deu."""

    servico = montar_servico(MockLLMProvider())
    informado = uuid4()

    outcome = await servico.structure_course(DEMANDA, execution_id=informado)

    assert outcome.execution_id == informado
    assert consultar_registros_de_execucao(informado)


# ----------------------------------------------------------------------
# Caminho de falha: hoje nao havia nenhum registro - este e o gap fechado
# ----------------------------------------------------------------------


async def test_chamada_que_esgota_retentativas_tambem_fica_recuperavel(
    montar_servico: MontarServico,
) -> None:
    falha = LLMUnavailableError(provider="programado", model="modelo-remoto-1")
    servico = montar_servico(_ProviderQueSempreFalha(falha), llm_max_retries=2)

    outcome = await servico.structure_course(DEMANDA)

    assert not outcome.succeeded
    registros = consultar_registros_de_execucao(outcome.execution_id)
    assert len(registros) == 1
    registro = registros[0]

    assert registro["nivel"] == "WARNING"
    assert registro["execution_id"] == str(outcome.execution_id)
    assert registro["demand_id"] == "dem-2026-0099"
    assert registro["provider"] == "programado"
    assert registro["model"] == "modelo-remoto-1"
    assert registro["tentativas"] == 3
    assert registro["erro_codigo"] == "LLM_UNAVAILABLE"
    assert registro["erro_classe"] == "LLMUnavailableError"
    # Sem resultado do provedor, nao ha token a reportar - omitido, nao inventado.
    assert "tokens_entrada" not in registro
    assert "tokens_saida" not in registro


async def test_falha_sem_provider_nem_model_no_erro_nao_inventa_valor(
    montar_servico: MontarServico,
) -> None:
    """Falha tipada sem ``provider``/``model`` proprios nao aparece com valor forjado."""

    servico = montar_servico(_ProviderQueSempreFalha(LLMUnavailableError()))

    outcome = await servico.structure_course(DEMANDA)

    registro = consultar_registros_de_execucao(outcome.execution_id)[0]
    assert "provider" not in registro
    assert "model" not in registro


# ----------------------------------------------------------------------
# RNF10/RNF11: o registro recuperavel nao vira vazamento
# ----------------------------------------------------------------------


async def test_registro_recuperavel_nao_contem_texto_do_cliente_nem_credencial(
    montar_servico: MontarServico,
) -> None:
    servico = montar_servico(MockLLMProvider())

    outcome = await servico.structure_course(DEMANDA)

    registro_serializado = json.dumps(consultar_registros_de_execucao(outcome.execution_id))
    for termo in TERMOS_DO_CLIENTE:
        assert termo not in registro_serializado
    assert "llm_api_key" not in registro_serializado.casefold()
    assert "authorization" not in registro_serializado.casefold()
