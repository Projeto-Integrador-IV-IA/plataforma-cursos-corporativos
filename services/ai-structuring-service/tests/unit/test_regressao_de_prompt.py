"""Regressao de acuracia entre versoes de prompt (RNF30, card #223).

O que estes testes protegem, em uma frase: uma versao de prompt mais nova que
piora um campo que uma versao mais antiga acertava tem de ser apontada, e uma
troca que nao piora nada tem de sair "sem regressao" - sem falso positivo por
ordenar versao como texto (``v10`` < ``v9`` lexicograficamente) e sem deixar
``substituido`` furar a politica escolhida para o conjunto comparado.
"""

from __future__ import annotations

from datetime import date
from typing import Any

import pytest

from app.core.config import Settings
from app.evaluation.catalog import ModeloCandidato
from app.evaluation.dataset import CasoDeAvaliacao, Procedencia
from app.evaluation.metrics import Medicao
from app.evaluation.regressao_de_prompt import (
    ComparacaoDeVersoesDePrompt,
    Regressao,
    comparar_versoes_de_prompt,
    numero_da_versao,
    versoes_do_catalogo,
)
from app.providers.mock_provider import MockLLMProvider

MODELO = ModeloCandidato(
    slug="vendor/modelo-referencia",
    apelido="Modelo de referencia",
    justificativa="fixo para a comparacao - a variavel sob teste e o prompt",
    janela_de_contexto=128_000,
    usd_por_mtok_entrada=1.0,
    usd_por_mtok_saida=2.0,
    preco_consultado_em=date(2026, 10, 16),
)


def medicao(acuracia_por_campo: dict[str, float | None], **sobrescreve: Any) -> Medicao:
    dados: dict[str, Any] = {"modelo": MODELO.slug, "casos": 10}
    dados.update(sobrescreve)
    return Medicao(acuracia_por_campo=acuracia_por_campo, **dados)


def caso_sintetico(identificador: str = "c1") -> CasoDeAvaliacao:
    return CasoDeAvaliacao(
        identificador=identificador,
        canal="emails",
        procedencia=Procedencia.SINTETICO,
        texto="demanda de treinamento qualquer, para exercitar o arnes",
        esperado={"carga_horaria": 16, "formato": "presencial"},
        sem_base=frozenset(),
    )


def fabrica_mock(slug: str, _settings: Settings) -> MockLLMProvider:
    return MockLLMProvider(model=slug)


class TestNumeroDaVersao:
    def test_ordena_por_numero_nao_por_texto(self) -> None:
        """v10 e mais nova que v9 - comparacao de string erraria isso."""

        assert numero_da_versao("v10") > numero_da_versao("v9")
        assert sorted(["v9", "v10", "v2"], key=numero_da_versao) == ["v2", "v9", "v10"]

    def test_versao_fora_do_formato_levanta_erro(self) -> None:
        with pytest.raises(ValueError, match="invalida"):
            numero_da_versao("beta")


class TestComparacaoDeVersoesDePromptComMedicoesFabricadas:
    """Testa a logica de comparacao isolada, sobre ``Medicao`` fabricada.

    Fabricar a medicao em vez de rodar o pipeline de novo e o jeito
    deterministico de testar so a comparacao: o cenario de regressao real
    (uma versao que piora um campo) nao depende de nenhum provedor real nem do
    conjunto de avaliacao - so do calculo em si.
    """

    def test_aponta_regressao_quando_versao_nova_cai_mais_de_5_pontos(self) -> None:
        comparacao = ComparacaoDeVersoesDePrompt(
            medicoes={
                "v1": medicao({"carga_horaria": 1.0, "formato": 1.0}),
                "v2": medicao({"carga_horaria": 0.5, "formato": 1.0}),
            }
        )

        regressoes = comparacao.regressoes
        assert len(regressoes) == 1
        regressao = regressoes[0]
        assert regressao == Regressao(
            campo="carga_horaria",
            versao_anterior="v1",
            versao_nova="v2",
            acuracia_anterior=1.0,
            acuracia_nova=0.5,
        )
        assert regressao.queda == pytest.approx(0.5)
        assert comparacao.reprova() is True

    def test_sem_regressao_quando_a_queda_fica_dentro_do_limiar(self) -> None:
        """Diferenca de 3 p.p. e ruido de amostra pequena, nao regressao."""

        comparacao = ComparacaoDeVersoesDePrompt(
            medicoes={
                "v1": medicao({"carga_horaria": 0.90}),
                "v2": medicao({"carga_horaria": 0.87}),
            }
        )

        assert comparacao.regressoes == ()
        assert comparacao.reprova() is False

    def test_sem_regressao_quando_versao_nova_melhora_ou_mantem(self) -> None:
        comparacao = ComparacaoDeVersoesDePrompt(
            medicoes={
                "v1": medicao({"carga_horaria": 0.6, "formato": 0.8}),
                "v2": medicao({"carga_horaria": 0.6, "formato": 1.0}),
                "v3": medicao({"carga_horaria": 0.9, "formato": 1.0}),
            }
        )

        assert comparacao.regressoes == ()
        assert comparacao.reprova() is False

    def test_compara_toda_versao_mais_antiga_nao_so_a_consecutiva(self) -> None:
        """v3 nao piorou frente a v2, mas carrega a regressao que v2 introduziu."""

        comparacao = ComparacaoDeVersoesDePrompt(
            medicoes={
                "v1": medicao({"carga_horaria": 1.0}),
                "v2": medicao({"carga_horaria": 0.5}),
                "v3": medicao({"carga_horaria": 0.5}),
            }
        )

        campos_e_pares = {(r.versao_anterior, r.versao_nova) for r in comparacao.regressoes}
        assert ("v1", "v2") in campos_e_pares
        assert ("v1", "v3") in campos_e_pares

    def test_versao_sem_medicao_para_o_campo_nao_participa_da_comparacao(self) -> None:
        """None e 'nao medido', nao zero - nao pode gerar regressao fantasma."""

        comparacao = ComparacaoDeVersoesDePrompt(
            medicoes={
                "v1": medicao({"carga_horaria": None}),
                "v2": medicao({"carga_horaria": 0.4}),
            }
        )

        assert comparacao.regressoes == ()

    def test_versao_nova_sem_medicao_para_o_campo_tambem_nao_participa(self) -> None:
        """Mesmo criterio do teste acima, com o lado que falta medicao invertido."""

        comparacao = ComparacaoDeVersoesDePrompt(
            medicoes={
                "v1": medicao({"carga_horaria": 0.9}),
                "v2": medicao({"carga_horaria": None}),
            }
        )

        assert comparacao.regressoes == ()

    def test_por_campo_devolve_acuracia_de_cada_versao_na_ordem_de_versao(self) -> None:
        comparacao = ComparacaoDeVersoesDePrompt(
            medicoes={
                "v2": medicao({"carga_horaria": 0.5}),
                "v1": medicao({"carga_horaria": 1.0}),
            }
        )

        assert list(comparacao.por_campo("carga_horaria").items()) == [
            ("v1", 1.0),
            ("v2", 0.5),
        ]

    def test_versoes_ordenadas_usa_numero_nao_texto(self) -> None:
        comparacao = ComparacaoDeVersoesDePrompt(
            medicoes={
                "v10": medicao({}),
                "v2": medicao({}),
                "v9": medicao({}),
            }
        )

        assert comparacao.versoes_ordenadas == ("v2", "v9", "v10")


class TestVersoesDoCatalogo:
    """Politica de inclusao de versao 'substituido' no conjunto comparado."""

    def test_por_padrao_inclui_versao_substituida(self) -> None:
        versoes = versoes_do_catalogo("extract-requirements")

        assert versoes == ("v1", "v2", "v3")

    def test_apenas_ativas_exclui_versao_substituida(self) -> None:
        versoes = versoes_do_catalogo("extract-requirements", apenas_ativas=True)

        assert versoes == ("v3",)

    def test_prompt_inexistente_devolve_tupla_vazia(self) -> None:
        assert versoes_do_catalogo("prompt-que-nao-existe") == ()


class TestCompararVersoesDePromptIntegracao:
    """Prova a fiacao: a comparacao de alto nivel chama o pipeline real.

    O provedor mock devolve sempre a mesma saida fixa, independente do prompt
    enviado (ver ``app/providers/mock_provider.py``) - de proposito, para a
    CI ser deterministica e nao custar chamada de API. Por isso, rodar versoes
    reais do catalogo contra o mock nunca mostra regressao real de conteudo;
    o que este teste prova e que ``comparar_versoes_de_prompt`` de fato chama
    ``runner.executar``/``StructuringService.structure_course`` para cada
    versao pedida - o cenario de regressao em si fica no teste acima, sobre
    ``Medicao`` fabricada, que isola a logica de comparacao do pipeline.
    """

    async def test_roda_o_pipeline_real_para_cada_versao_do_catalogo(self, make_settings) -> None:
        casos = [caso_sintetico("c1"), caso_sintetico("c2")]

        comparacao = await comparar_versoes_de_prompt(
            nome_do_prompt="extract-requirements",
            versoes=versoes_do_catalogo("extract-requirements"),
            casos=casos,
            modelo=MODELO,
            fabrica_de_provedor=fabrica_mock,
            settings=make_settings(),
        )

        assert comparacao.versoes_ordenadas == ("v1", "v2", "v3")
        for versao in comparacao.versoes_ordenadas:
            assert comparacao.medicoes[versao].casos == len(casos)
        # Mock e deterministico entre versoes de prompt: nao ha regressao real
        # de conteudo para detectar aqui, so a fiacao com o caso de uso real.
        assert comparacao.regressoes == ()

    async def test_versoes_vazias_devolve_comparacao_vazia(self, make_settings) -> None:
        comparacao = await comparar_versoes_de_prompt(
            nome_do_prompt="extract-requirements",
            versoes=(),
            casos=[caso_sintetico()],
            modelo=MODELO,
            fabrica_de_provedor=fabrica_mock,
            settings=make_settings(),
        )

        assert comparacao.medicoes == {}
        assert comparacao.regressoes == ()
