"""Numeracao de trechos citaveis da fonte (RF28, cards #153/#154).

O que estes testes protegem: a entrada que chega ao provedor tem de numerar os
mesmos trechos que a validacao de ``evidencias`` depois espera encontrar - um
desalinhamento aqui faria toda citacao do modelo apontar para o trecho errado.
"""

from app.providers import MockLLMProvider
from app.services.structuring_service import (
    RawDemand,
    StructuringService,
    formatar_trechos_numerados,
    numerar_trechos,
)
from tests.conftest import MakeSettings


class TestNumerarTrechos:
    def test_uma_linha_e_um_trecho(self) -> None:
        assert numerar_trechos("uma linha so") == ("uma linha so",)

    def test_cada_linha_nao_vazia_e_um_trecho(self) -> None:
        texto = "primeira linha\nsegunda linha\nterceira linha"

        assert numerar_trechos(texto) == ("primeira linha", "segunda linha", "terceira linha")

    def test_linha_em_branco_nao_e_trecho(self) -> None:
        texto = "primeira linha\n\n\nsegunda linha"

        assert numerar_trechos(texto) == ("primeira linha", "segunda linha")

    def test_espaco_nas_bordas_da_linha_e_removido(self) -> None:
        assert numerar_trechos("  linha com espaco nas bordas  ") == (
            "linha com espaco nas bordas",
        )

    def test_texto_vazio_nao_produz_trecho(self) -> None:
        assert numerar_trechos("") == ()
        assert numerar_trechos("   \n\n   ") == ()


class TestFormatarTrechosNumerados:
    def test_numeracao_comeca_em_um(self) -> None:
        formatado = formatar_trechos_numerados(("primeiro", "segundo"))

        assert formatado == "[1] primeiro\n[2] segundo"

    def test_lista_vazia_produz_texto_vazio(self) -> None:
        assert formatar_trechos_numerados(()) == ""

    def test_numero_do_trecho_corresponde_a_posicao_na_lista(self) -> None:
        """E o que a validacao de evidencias depois assume: trechos[n - 1] e o numero n."""

        trechos = numerar_trechos("alfa\nbeta\ngama")
        formatado = formatar_trechos_numerados(trechos)

        for numero, trecho in enumerate(trechos, start=1):
            assert f"[{numero}] {trecho}" in formatado


async def test_structure_course_envia_a_entrada_numerada_e_guarda_os_trechos(
    make_settings: MakeSettings,
) -> None:
    """``outcome.trechos`` precisa estar alinhado com o que o provedor recebeu."""

    class _ProviderEspiao(MockLLMProvider):
        def __init__(self) -> None:
            super().__init__()
            self.recebido: str | None = None

        async def complete(self, prompt, params=None):  # type: ignore[override]
            self.recebido = prompt
            return await super().complete(prompt, params)

    provider = _ProviderEspiao()
    servico = StructuringService(provider, make_settings())
    demanda = RawDemand(demand_id="dem-2026-0042", text="primeira linha\nsegunda linha")

    outcome = await servico.structure_course(demanda)

    assert outcome.trechos == ("primeira linha", "segunda linha")
    assert provider.recebido is not None
    assert "[1] primeira linha" in provider.recebido
    assert "[2] segunda linha" in provider.recebido
