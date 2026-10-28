"""Barreira de evidencia antes de persistir: recusa, diagnostico e sigilo (RNF27).

RNF27 na matriz de rastreabilidade; **RF28** no Documento Consolidado de
Requisitos v1.0, cards #153-#156.

O que estes testes protegem: nao basta o modelo citar um trecho em
``evidencias``, a citacao tem de existir entre os trechos que de fato foram
enviados nesta chamada. Citacao forjada (numero fora do intervalo) e recusada
antes de virar resultado - mesma regra de RNF05.1, agora aplicada a
evidencia -, e a recusa fica registrada em log para diagnostico sem repetir o
texto do cliente.

O provedor e sempre o mock. Nenhum teste toca rede, chave ou custo (RNF12).
"""

import json
import logging
from collections.abc import Callable

import pytest

from app.core.exceptions import LLMInvalidResponseError
from app.providers import MockLLMProvider
from app.services.structuring_service import RawDemand, StructuringService
from tests.conftest import MakeSettings

LOGGER_DO_CASO_DE_USO = "app.services.structuring_service"

#: Dois trechos: numeros validos para esta demanda sao 1 e 2, nenhum outro.
TEXTO_COLADO = """
Precisamos de um treinamento de NR-12 para a manutencao.
Uns 25 tecnicos, em dois dias de 8 horas.
"""

DEMANDA = RawDemand(demand_id="dem-2026-0042", text=TEXTO_COLADO)

#: Cita o trecho 1 (valido) e o 99, que nunca existiu nesta chamada.
RESPOSTA_COM_CITACAO_FORJADA = json.dumps(
    {
        "tema": "NR-12",
        "publico_alvo": None,
        "carga_horaria": 16,
        "objetivos_aprendizagem": [],
        "ementa": [],
        "campos_ausentes": [
            {"campo": "publico_alvo", "tipo": "ausente", "motivo": "nao declarado."},
            {"campo": "objetivos_aprendizagem", "tipo": "ausente", "motivo": "nao declarado."},
            {"campo": "ementa", "tipo": "ausente", "motivo": "nao declarado."},
        ],
        "procedencia": {"tema": "extraido", "carga_horaria": "inferido"},
        "evidencias": {"tema": [1], "carga_horaria": [99]},
        "observacoes": [],
    }
)

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
# Criterio de aceite: citacao forjada e recusada e nao e persistida
# ----------------------------------------------------------------------


async def test_citacao_de_trecho_inexistente_e_recusada(montar_servico: MontarServico) -> None:
    """Criterio de aceite: saida com ID inexistente e recusada e nao e persistida."""

    servico = montar_servico(RESPOSTA_COM_CITACAO_FORJADA)

    outcome = await servico.structure_course(DEMANDA)

    assert not outcome.succeeded
    assert outcome.course is None
    assert isinstance(outcome.error, LLMInvalidResponseError)


async def test_erro_identifica_qual_citacao_falhou(montar_servico: MontarServico) -> None:
    """Criterio de aceite: o erro identifica qual citacao falhou."""

    servico = montar_servico(RESPOSTA_COM_CITACAO_FORJADA)

    outcome = await servico.structure_course(DEMANDA)

    assert outcome.error is not None
    assert isinstance(outcome.error, LLMInvalidResponseError)
    assert outcome.error.citacoes_invalidas() == ({"campo": "carga_horaria", "numero": 99},)


def test_citacoes_invalidas_vazio_quando_a_falha_nao_veio_dessa_checagem() -> None:
    """Falha de outra origem (corpo ilegivel, por exemplo) nao tem citacao a listar."""

    assert LLMInvalidResponseError("corpo ilegivel").citacoes_invalidas() == ()


async def test_citacao_dentro_do_intervalo_nao_e_recusada(montar_servico: MontarServico) -> None:
    """So a citacao fora do intervalo falha - citar 1 ou 2 nesta demanda e valido."""

    valida = json.dumps(
        {
            "tema": "NR-12",
            "publico_alvo": None,
            "carga_horaria": 16,
            "objetivos_aprendizagem": [],
            "ementa": [],
            "campos_ausentes": [
                {"campo": "publico_alvo", "tipo": "ausente", "motivo": "nao declarado."},
                {"campo": "objetivos_aprendizagem", "tipo": "ausente", "motivo": "nao declarado."},
                {"campo": "ementa", "tipo": "ausente", "motivo": "nao declarado."},
            ],
            "procedencia": {"tema": "extraido", "carga_horaria": "inferido"},
            "evidencias": {"tema": [1], "carga_horaria": [2]},
            "observacoes": [],
        }
    )
    servico = montar_servico(valida)

    outcome = await servico.structure_course(DEMANDA)

    assert outcome.succeeded
    assert outcome.course is not None


async def test_citacao_de_numero_zero_e_recusada(montar_servico: MontarServico) -> None:
    """A numeracao comeca em 1 - citar 0 e fora do intervalo como citar 99."""

    zero = json.dumps(
        {
            "tema": "NR-12",
            "publico_alvo": None,
            "carga_horaria": None,
            "objetivos_aprendizagem": [],
            "ementa": [],
            "campos_ausentes": [
                {"campo": "publico_alvo", "tipo": "ausente", "motivo": "nao declarado."},
                {"campo": "carga_horaria", "tipo": "ausente", "motivo": "nao declarado."},
                {"campo": "objetivos_aprendizagem", "tipo": "ausente", "motivo": "nao declarado."},
                {"campo": "ementa", "tipo": "ausente", "motivo": "nao declarado."},
            ],
            "procedencia": {"tema": "extraido"},
            "evidencias": {"tema": [0]},
            "observacoes": [],
        }
    )
    servico = montar_servico(zero)

    outcome = await servico.structure_course(DEMANDA)

    assert not outcome.succeeded
    assert outcome.error is not None
    assert isinstance(outcome.error, LLMInvalidResponseError)
    assert outcome.error.citacoes_invalidas() == ({"campo": "tema", "numero": 0},)


# ----------------------------------------------------------------------
# Criterio de aceite: a recusa e registrada em log, sem o texto do cliente
# ----------------------------------------------------------------------


async def test_citacao_invalida_e_registrada_em_log(
    montar_servico: MontarServico,
    caplog: pytest.LogCaptureFixture,
) -> None:
    """Criterio de aceite: registrar no log a citacao invalida, para diagnostico."""

    servico = montar_servico(RESPOSTA_COM_CITACAO_FORJADA, llm_schema_max_retries=0)

    with caplog.at_level(logging.WARNING, logger=LOGGER_DO_CASO_DE_USO):
        await servico.structure_course(DEMANDA)

    alertas = [registro for registro in caplog.records if registro.levelno == logging.WARNING]
    assert len(alertas) == 1
    registro = alertas[0].getMessage()
    assert "dem-2026-0042" in registro
    assert "carga_horaria:99" in registro


async def test_log_da_citacao_invalida_nao_repete_o_texto_do_cliente(
    montar_servico: MontarServico,
    caplog: pytest.LogCaptureFixture,
) -> None:
    """RNF10: o alerta de rotina identifica a falha sem citar o que o cliente escreveu."""

    servico = montar_servico(RESPOSTA_COM_CITACAO_FORJADA)

    with caplog.at_level(logging.WARNING, logger=LOGGER_DO_CASO_DE_USO):
        await servico.structure_course(DEMANDA)

    alertas = [registro for registro in caplog.records if registro.levelno == logging.WARNING]
    registro = alertas[0].getMessage()
    assert "NR-12" not in registro
    assert "manutencao" not in registro
