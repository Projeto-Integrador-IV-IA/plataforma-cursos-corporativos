"""Agregacao diaria de consumo de tokens e alerta de teto (RNF22, card #22).

O que estes testes protegem: tokens de chamadas sucessivas somam no mesmo dia,
dias diferentes ficam isolados um do outro, e o teto configurado - quando
ultrapassado - vira um registro em ``WARNING`` no log, nunca uma excecao (o
alerta e observabilidade, nao controle de fluxo).

``ConsumoDeLLM`` e testado por instancia propria, nunca pelo singleton de
modulo: cada teste comeca de um acumulado zerado, sem depender da ordem de
execucao dos outros arquivos de teste.
"""

from datetime import UTC, date, datetime

import pytest

from app.core.consumption import ConsumoDeLLM, consultar_consumo, registrar_consumo


@pytest.fixture(autouse=True)
def _consumo_isolado(monkeypatch: pytest.MonkeyPatch) -> None:
    """Troca o singleton de modulo por uma instancia nova a cada teste.

    Sem isto, ``registrar_consumo``/``consultar_consumo`` (usadas abaixo para
    testar os wrappers de modulo) acumulariam no mesmo acumulado global que
    outros arquivos de teste tambem tocam.
    """

    monkeypatch.setattr("app.core.consumption._consumo", ConsumoDeLLM())


DIA_1 = datetime(2026, 11, 12, 10, 0, tzinfo=UTC)
DIA_1_MAIS_TARDE = datetime(2026, 11, 12, 23, 59, tzinfo=UTC)
DIA_2 = datetime(2026, 11, 13, 0, 1, tzinfo=UTC)


# ----------------------------------------------------------------------
# ConsumoDeLLM: agregacao por dia civil (UTC)
# ----------------------------------------------------------------------


def test_chamadas_do_mesmo_dia_somam() -> None:
    tracker = ConsumoDeLLM()

    tracker.registrar(tokens_entrada=100, tokens_saida=20, quando=DIA_1)
    acumulado = tracker.registrar(tokens_entrada=50, tokens_saida=10, quando=DIA_1_MAIS_TARDE)

    assert acumulado.dia == date(2026, 11, 12)
    assert acumulado.chamadas == 2
    assert acumulado.tokens_entrada == 150
    assert acumulado.tokens_saida == 30
    assert acumulado.tokens_totais == 180


def test_dias_diferentes_ficam_isolados() -> None:
    tracker = ConsumoDeLLM()

    tracker.registrar(tokens_entrada=100, tokens_saida=20, quando=DIA_1)
    tracker.registrar(tokens_entrada=999, tokens_saida=999, quando=DIA_2)

    consumo_dia_1 = tracker.do_dia(date(2026, 11, 12))
    assert consumo_dia_1.chamadas == 1
    assert consumo_dia_1.tokens_totais == 120


def test_dia_sem_chamada_devolve_consumo_zerado_nao_erro() -> None:
    tracker = ConsumoDeLLM()

    consumo = tracker.do_dia(date(2026, 1, 1))

    assert consumo.chamadas == 0
    assert consumo.tokens_totais == 0


def test_do_dia_sem_argumento_usa_hoje_em_utc() -> None:
    tracker = ConsumoDeLLM()
    tracker.registrar(tokens_entrada=10, tokens_saida=5)

    consumo = tracker.do_dia()

    assert consumo.dia == datetime.now(UTC).date()
    assert consumo.tokens_totais == 15


# ----------------------------------------------------------------------
# registrar_consumo: alerta de teto diario
# ----------------------------------------------------------------------


def test_sem_limite_configurado_nao_alerta(caplog: pytest.LogCaptureFixture) -> None:
    with caplog.at_level("WARNING"):
        registrar_consumo(tokens_entrada=10_000, tokens_saida=10_000, limite_diario=None)

    assert caplog.records == []


def test_consumo_dentro_do_limite_nao_alerta(caplog: pytest.LogCaptureFixture) -> None:
    with caplog.at_level("WARNING"):
        registrar_consumo(tokens_entrada=100, tokens_saida=100, limite_diario=1_000)

    assert caplog.records == []


def test_consumo_acima_do_limite_registra_alerta_no_log(caplog: pytest.LogCaptureFixture) -> None:
    with caplog.at_level("WARNING"):
        registrar_consumo(tokens_entrada=600, tokens_saida=500, limite_diario=1_000)

    assert len(caplog.records) == 1
    mensagem = caplog.records[0].message
    assert "Limite diario" in mensagem
    assert "1100" in mensagem or "1000" in mensagem


def test_consumo_acumulado_que_ultrapassa_limite_tambem_alerta(
    caplog: pytest.LogCaptureFixture,
) -> None:
    """O teto vigia o acumulado do dia, nao so a chamada isolada."""

    registrar_consumo(tokens_entrada=600, tokens_saida=0, limite_diario=1_000)

    with caplog.at_level("WARNING"):
        registrar_consumo(tokens_entrada=600, tokens_saida=0, limite_diario=1_000)

    assert len(caplog.records) == 1


# ----------------------------------------------------------------------
# consultar_consumo: leitura publica do acumulado do singleton de modulo
# ----------------------------------------------------------------------


def test_consultar_consumo_reflete_o_que_foi_registrado() -> None:
    registrar_consumo(tokens_entrada=300, tokens_saida=70, limite_diario=None)

    consumo = consultar_consumo()

    assert consumo.chamadas == 1
    assert consumo.tokens_entrada == 300
    assert consumo.tokens_saida == 70
