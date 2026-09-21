"""Barreira de schema antes de persistir: recusa, diagnostico e sigilo (RNF05).

RNF05 na matriz de rastreabilidade; **RNF05.1** no Documento Consolidado de
Requisitos v1.0.

O que estes testes protegem: quando o provedor devolve algo fora do schema do
curso estruturado, a resposta e recusada, a recusa vira registro de log
utilizavel para diagnostico, o erro devolvido nomeia o campo que violou o
contrato - e nem o texto do cliente nem a chave do provedor viajam no corpo da
resposta.

A divisao de niveis e o ponto: o alerta de rotina descreve a falha sem repetir
o que o cliente escreveu (RNF10, RNF11); a resposta bruta so aparece em
``DEBUG``, truncada, para quem ligou o nivel de proposito para investigar.

O provedor e sempre o mock ou um transporte HTTP dublado. Nenhum teste toca
rede, chave ou custo (RNF12).
"""

import json
import logging
from collections.abc import Callable

import httpx
import pytest

from app.core.exceptions import LLMInvalidResponseError
from app.providers import HttpLLMProvider, MockLLMProvider
from app.services.structuring_service import (
    DEFAULT_PROMPT_VERSION,
    EXTRACTION_PROMPT_NAME,
    RAW_RESPONSE_LOG_LIMIT,
    RawDemand,
    StructuringService,
)
from tests.conftest import MakeSettings

LOGGER_DO_CASO_DE_USO = "app.services.structuring_service"

TEXTO_COLADO = """
Boa tarde! Precisamos de um treinamento de NR-12 para os 25 tecnicos da manutencao da planta 2
da Metalurgica Aurora, em dois dias de 8 horas, no proprio site.
"""

DEMANDA = RawDemand(demand_id="dem-2026-0042", text=TEXTO_COLADO)

#: Termos do texto do cliente que nao podem reaparecer em log de rotina nem no
#: corpo de erro devolvido ao operador.
TERMOS_DO_CLIENTE = ("NR-12", "Metalurgica Aurora", "planta 2")

#: Resposta "quase certa": chave do contrato preenchida, chave inventada junto e
#: as obrigatorias faltando. E o caso que o card pede - o que nao passa no
#: schema nao pode virar resultado.
RESPOSTA_FORA_DO_SCHEMA = '{"tema": "NR-12 na Metalurgica Aurora", "sobrando": true}'

MontarServico = Callable[..., StructuringService]


@pytest.fixture
def montar_servico(make_settings: MakeSettings) -> MontarServico:
    """Monta o caso de uso sobre o provedor mock, sem dormir entre tentativas."""

    def _montar(response_text: str, **overrides: object) -> StructuringService:
        base: dict[str, object] = {"llm_max_retries": 0}
        base.update(overrides)
        return StructuringService(
            MockLLMProvider(response_text=response_text),
            make_settings(**base),
            sleep=_nao_dormir,
        )

    return _montar


async def _nao_dormir(segundos: float) -> None:
    """Espera de mentira: a politica de retentativa nao atrasa o teste."""


# ----------------------------------------------------------------------
# Criterio de aceite: a recusa e registrada em log
# ----------------------------------------------------------------------


async def test_resposta_fora_do_schema_e_registrada_em_log(
    montar_servico: MontarServico,
    caplog: pytest.LogCaptureFixture,
) -> None:
    """Criterio de aceite: a recusa nao passa silenciosa - fica no log."""

    servico = montar_servico(RESPOSTA_FORA_DO_SCHEMA)

    with caplog.at_level(logging.WARNING, logger=LOGGER_DO_CASO_DE_USO):
        outcome = await servico.structure_course(DEMANDA)

    alertas = [registro for registro in caplog.records if registro.levelno == logging.WARNING]
    assert not outcome.succeeded
    assert len(alertas) == 1
    registro = alertas[0].getMessage()
    assert "dem-2026-0042" in registro
    # Derivado do catalogo: fixar o numero quebraria a cada prompt novo.
    assert f"{EXTRACTION_PROMPT_NAME}.{DEFAULT_PROMPT_VERSION}" in registro
    assert "sobrando" in registro


async def test_alerta_da_recusa_nomeia_os_campos_que_violaram_o_contrato(
    montar_servico: MontarServico,
    caplog: pytest.LogCaptureFixture,
) -> None:
    """Sem os campos no log, saber "o que veio errado" exige rodar de novo."""

    servico = montar_servico('{"tema": "NR-12", "carga_horaria": "dois dias"}')

    with caplog.at_level(logging.WARNING, logger=LOGGER_DO_CASO_DE_USO):
        await servico.structure_course(DEMANDA)

    registro = caplog.records[0].getMessage()
    assert "carga_horaria" in registro
    assert "publico_alvo" in registro


async def test_resposta_valida_nao_gera_alerta(
    montar_servico: MontarServico,
    caplog: pytest.LogCaptureFixture,
) -> None:
    """Caminho feliz nao polui o log: alerta so quando ha recusa."""

    servico = montar_servico(MockLLMProvider().response_text)

    with caplog.at_level(logging.DEBUG, logger=LOGGER_DO_CASO_DE_USO):
        outcome = await servico.structure_course(DEMANDA)

    assert outcome.succeeded
    assert caplog.records == []


# ----------------------------------------------------------------------
# O log de diagnostico nao vira vazamento (RNF10, RNF11)
# ----------------------------------------------------------------------


async def test_log_de_rotina_nao_repete_o_texto_do_cliente(
    montar_servico: MontarServico,
    caplog: pytest.LogCaptureFixture,
) -> None:
    """RNF10: no nivel de sempre, o log descreve a falha - nao a demanda."""

    servico = montar_servico(RESPOSTA_FORA_DO_SCHEMA)

    with caplog.at_level(logging.WARNING, logger=LOGGER_DO_CASO_DE_USO):
        await servico.structure_course(DEMANDA)

    registrado = "\n".join(registro.getMessage() for registro in caplog.records)
    for termo in TERMOS_DO_CLIENTE:
        assert termo not in registrado


async def test_resposta_bruta_so_aparece_no_nivel_de_diagnostico(
    montar_servico: MontarServico,
    caplog: pytest.LogCaptureFixture,
) -> None:
    """A resposta recusada existe no log, mas atras de ``LOG_LEVEL=DEBUG``."""

    servico = montar_servico(RESPOSTA_FORA_DO_SCHEMA)

    with caplog.at_level(logging.DEBUG, logger=LOGGER_DO_CASO_DE_USO):
        await servico.structure_course(DEMANDA)

    diagnosticos = [
        registro.getMessage() for registro in caplog.records if registro.levelno == logging.DEBUG
    ]
    assert len(diagnosticos) == 1
    assert RESPOSTA_FORA_DO_SCHEMA in diagnosticos[0]
    assert "dem-2026-0042" in diagnosticos[0]


async def test_resposta_bruta_longa_e_truncada_no_log(
    montar_servico: MontarServico,
    caplog: pytest.LogCaptureFixture,
) -> None:
    """Resposta enorme nao derruba o arquivo de log nem despeja a demanda inteira."""

    enchimento = "x" * (RAW_RESPONSE_LOG_LIMIT * 3)
    servico = montar_servico(f'{{"tema": "{enchimento}", "sobrando": true}}')

    with caplog.at_level(logging.DEBUG, logger=LOGGER_DO_CASO_DE_USO):
        await servico.structure_course(DEMANDA)

    diagnostico = next(
        registro.getMessage() for registro in caplog.records if registro.levelno == logging.DEBUG
    )
    assert "caracteres truncados" in diagnostico
    assert diagnostico.count("x") == RAW_RESPONSE_LOG_LIMIT - len('{"tema": "')


# ----------------------------------------------------------------------
# Criterio de aceite: o erro devolvido identifica o campo violado
# ----------------------------------------------------------------------


async def test_erro_devolvido_identifica_o_campo_que_violou_o_contrato(
    montar_servico: MontarServico,
) -> None:
    """Criterio de aceite: quem recebe o 502 sabe qual campo quebrou o contrato."""

    servico = montar_servico(RESPOSTA_FORA_DO_SCHEMA)

    outcome = await servico.structure_course(DEMANDA)
    payload = outcome.to_error_payload()

    assert isinstance(outcome.error, LLMInvalidResponseError)
    assert payload is not None
    detalhes = payload["error"]["details"]
    assert detalhes["demand_id"] == "dem-2026-0042"
    assert detalhes["retryable"] is False
    campos = {violacao["campo"] for violacao in detalhes["violacoes"]}
    assert "sobrando" in campos
    assert {"publico_alvo", "carga_horaria"} <= campos
    assert set(outcome.error.violated_fields()) == campos


def test_falha_sem_violacao_de_schema_nao_inventa_campo() -> None:
    """Resposta ilegivel nao tem campo a apontar - a lista sai vazia, nao errada."""

    assert LLMInvalidResponseError("corpo ilegivel").violated_fields() == ()


async def test_nada_e_devolvido_como_sucesso_quando_o_schema_recusa(
    montar_servico: MontarServico,
) -> None:
    """Criterio de aceite: fora do schema nao vira curso, nem pela metade."""

    servico = montar_servico(RESPOSTA_FORA_DO_SCHEMA)

    outcome = await servico.structure_course(DEMANDA)

    assert outcome.course is None
    assert not outcome.succeeded
    assert outcome.demand.text == TEXTO_COLADO
    with pytest.raises(LLMInvalidResponseError):
        outcome.raise_for_course()


# ----------------------------------------------------------------------
# Nem a chave do provedor nem o texto do cliente saem na resposta
# ----------------------------------------------------------------------


async def test_chave_e_texto_do_cliente_nao_vazam_na_recusa(
    make_settings: MakeSettings,
    caplog: pytest.LogCaptureFixture,
) -> None:
    """RNF10 e RNF11 no caminho da recusa, com provedor remoto dublado."""

    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(
            200,
            json={
                "model": "modelo-remoto-1",
                "choices": [
                    {"message": {"content": RESPOSTA_FORA_DO_SCHEMA}, "finish_reason": "stop"}
                ],
                "usage": {"prompt_tokens": 310, "completion_tokens": 128},
            },
        )

    settings = make_settings(
        llm_provider="http",
        llm_model="modelo-remoto-1",
        llm_api_key="chave-de-teste-do-ambiente",
        llm_base_url="https://api.exemplo.invalid/v1",
        llm_max_retries=0,
    )
    servico = StructuringService(
        HttpLLMProvider(settings, client=httpx.AsyncClient(transport=httpx.MockTransport(handler))),
        settings,
        sleep=_nao_dormir,
    )

    with caplog.at_level(logging.WARNING, logger=LOGGER_DO_CASO_DE_USO):
        outcome = await servico.structure_course(DEMANDA)

    corpo = json.dumps(outcome.to_error_payload(), ensure_ascii=False)
    alerta = "\n".join(registro.getMessage() for registro in caplog.records)

    assert "chave-de-teste-do-ambiente" not in corpo
    assert "chave-de-teste-do-ambiente" not in alerta
    assert "authorization" not in corpo.casefold()
    for termo in TERMOS_DO_CLIENTE:
        assert termo not in corpo
        assert termo not in alerta
