"""Execucao em lote do conjunto de avaliacao contra o catalogo (RNF29, card #217).

O que estes testes protegem: a rodada tem de ser retomavel sem rechamar o
provedor para o que ja foi feito, e o arquivo gravado tem de trazer o que torna
duas rodadas comparaveis - modelo, versao de prompt, versao de schema e data.
"""

from __future__ import annotations

from datetime import date
from pathlib import Path

from app.core.config import Settings
from app.domain.course import SCHEMA_VERSION
from app.evaluation.catalog import ModeloCandidato
from app.evaluation.dataset import CasoDeAvaliacao, Procedencia
from app.evaluation.metrics import Execucao
from app.evaluation.runner import carregar, executar, salvar
from app.providers.mock_provider import MockLLMProvider

MODELO_A = ModeloCandidato(
    slug="vendor/modelo-a",
    apelido="Modelo A",
    justificativa="referencia",
    janela_de_contexto=128_000,
    usd_por_mtok_entrada=1.0,
    usd_por_mtok_saida=2.0,
    preco_consultado_em=date(2026, 10, 16),
)
MODELO_B = ModeloCandidato(
    slug="vendor/modelo-b",
    apelido="Modelo B",
    justificativa="referencia",
    janela_de_contexto=128_000,
    usd_por_mtok_entrada=1.0,
    usd_por_mtok_saida=2.0,
    preco_consultado_em=date(2026, 10, 16),
)


def caso(identificador: str) -> CasoDeAvaliacao:
    return CasoDeAvaliacao(
        identificador=identificador,
        canal="emails",
        procedencia=Procedencia.SINTETICO,
        texto="demanda de treinamento qualquer",
        esperado={},
        sem_base=frozenset(),
    )


def fabrica_mock(slug: str, _settings: Settings) -> MockLLMProvider:
    return MockLLMProvider(model=slug)


class TestExecucao:
    async def test_cobre_cada_par_modelo_caso(self, make_settings) -> None:
        rodada = await executar(
            casos=[caso("c1"), caso("c2")],
            modelos=[MODELO_A, MODELO_B],
            fabrica_de_provedor=fabrica_mock,
            settings=make_settings(),
        )

        pares = {(e.modelo, e.caso) for e in rodada.execucoes}
        assert pares == {
            ("vendor/modelo-a", "c1"),
            ("vendor/modelo-a", "c2"),
            ("vendor/modelo-b", "c1"),
            ("vendor/modelo-b", "c2"),
        }

    async def test_repeticoes_multiplicam_as_execucoes_por_par(self, make_settings) -> None:
        rodada = await executar(
            casos=[caso("c1")],
            modelos=[MODELO_A],
            fabrica_de_provedor=fabrica_mock,
            settings=make_settings(),
            repeticoes=3,
        )

        assert rodada.total == 3
        assert all(e.modelo == "vendor/modelo-a" and e.caso == "c1" for e in rodada.execucoes)

    async def test_ja_feitas_pula_o_par_sem_chamar_o_provedor(self, make_settings) -> None:
        chamados: list[str] = []

        def fabrica_que_registra(slug: str, _settings: Settings) -> MockLLMProvider:
            chamados.append(slug)
            return MockLLMProvider(model=slug)

        rodada = await executar(
            casos=[caso("c1"), caso("c2")],
            modelos=[MODELO_A],
            fabrica_de_provedor=fabrica_que_registra,
            settings=make_settings(),
            ja_feitas=[("vendor/modelo-a", "c1")],
        )

        pares = {(e.modelo, e.caso) for e in rodada.execucoes}
        assert pares == {("vendor/modelo-a", "c2")}, (
            "par ja feito nao pode ser rechamado - e o que torna a rodada retomavel"
        )
        assert chamados == ["vendor/modelo-a"], (
            "a fabrica e por modelo, nao por par - pular um caso nao pode fazer o "
            "executor pedir um provedor extra"
        )

    async def test_ja_feitas_cobrindo_tudo_nao_chama_a_api_do_provedor(self, make_settings) -> None:
        chamadas: list[str] = []

        class ProvedorQueRegistraChamada(MockLLMProvider):
            async def complete(self, prompt, params=None):  # type: ignore[override]
                chamadas.append(prompt)
                return await super().complete(prompt, params)

        rodada = await executar(
            casos=[caso("c1")],
            modelos=[MODELO_A],
            fabrica_de_provedor=lambda slug, _settings: ProvedorQueRegistraChamada(model=slug),
            settings=make_settings(),
            ja_feitas=[("vendor/modelo-a", "c1")],
        )

        assert rodada.total == 0
        assert chamadas == [], (
            "par ja feito nao pode custar uma chamada de API - e o que torna a rodada retomavel"
        )

    async def test_ao_terminar_caso_e_chamado_uma_vez_por_execucao(self, make_settings) -> None:
        progresso: list[Execucao] = []

        await executar(
            casos=[caso("c1"), caso("c2")],
            modelos=[MODELO_A],
            fabrica_de_provedor=fabrica_mock,
            settings=make_settings(),
            ao_terminar_caso=progresso.append,
        )

        assert len(progresso) == 2

    async def test_falha_do_provedor_fica_registrada_e_nao_interrompe_a_rodada(
        self, make_settings
    ) -> None:
        from app.core.exceptions import LLMTimeoutError

        def fabrica_que_falha_para_b(slug: str, _settings: Settings) -> MockLLMProvider:
            if slug == "vendor/modelo-b":
                return MockLLMProvider(model=slug, fail_with=LLMTimeoutError("estourou"))
            return MockLLMProvider(model=slug)

        rodada = await executar(
            casos=[caso("c1")],
            modelos=[MODELO_A, MODELO_B],
            fabrica_de_provedor=fabrica_que_falha_para_b,
            settings=make_settings(),
        )

        por_modelo = {e.modelo: e for e in rodada.execucoes}
        assert por_modelo["vendor/modelo-a"].erro is None
        assert "estourou" in (por_modelo["vendor/modelo-b"].erro or "")

    async def test_registra_as_condicoes_da_rodada(self, make_settings) -> None:
        rodada = await executar(
            casos=[caso("c1")],
            modelos=[MODELO_A],
            fabrica_de_provedor=fabrica_mock,
            settings=make_settings(),
            prompt_version="v3",
        )

        assert rodada.prompt_version == "v3"
        assert rodada.schema_version == SCHEMA_VERSION
        assert rodada.modelos == ("vendor/modelo-a",)
        assert rodada.casos == ("c1",)
        assert rodada.iniciada_em is not None


class TestRetomadaDeArquivo:
    """O ciclo completo: gravar, reler e so pedir o que falta."""

    async def test_resultado_gravado_informa_ja_feitas_da_proxima_chamada(
        self, make_settings, tmp_path: Path
    ) -> None:
        destino = tmp_path / "rodada.json"

        primeira = await executar(
            casos=[caso("c1")],
            modelos=[MODELO_A],
            fabrica_de_provedor=fabrica_mock,
            settings=make_settings(),
        )
        salvar(primeira, destino)

        lida = carregar(destino)
        ja_feitas = [(e.modelo, e.caso) for e in lida.execucoes]

        segunda = await executar(
            casos=[caso("c1"), caso("c2")],
            modelos=[MODELO_A],
            fabrica_de_provedor=fabrica_mock,
            settings=make_settings(),
            ja_feitas=ja_feitas,
        )

        assert {(e.modelo, e.caso) for e in segunda.execucoes} == {("vendor/modelo-a", "c2")}

    async def test_rodada_gravada_preserva_versao_de_prompt_e_de_schema(
        self, make_settings, tmp_path: Path
    ) -> None:
        rodada = await executar(
            casos=[caso("c1")],
            modelos=[MODELO_A],
            fabrica_de_provedor=fabrica_mock,
            settings=make_settings(),
            prompt_version="v3",
        )

        destino = salvar(rodada, tmp_path / "rodada.json")
        lida = carregar(destino)

        assert lida.prompt_version == "v3"
        assert lida.schema_version == SCHEMA_VERSION
