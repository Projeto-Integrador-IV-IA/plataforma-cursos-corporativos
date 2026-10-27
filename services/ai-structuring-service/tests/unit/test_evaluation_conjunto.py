"""Carregamento do conjunto de avaliacao e do catalogo de modelos (RNF04).

O que estes testes protegem: um conjunto malformado tem de falhar na leitura, e
nao no meio de uma rodada que consome credito de API. Por isso quase todo caso
aqui e de recusa.
"""

from __future__ import annotations

import json
from datetime import date
from pathlib import Path

import pytest

from app.evaluation.catalog import (
    CatalogoInvalidoError,
    ModeloCandidato,
    carregar_catalogo,
    selecionar,
)
from app.evaluation.dataset import (
    ConjuntoInvalidoError,
    Procedencia,
    carregar_conjunto,
)

GABARITO_MINIMO = {
    "procedencia": "sintetico",
    "esperado": {"tema": "lideranca", "carga_horaria": 16},
    "sem_base": ["formato"],
}


def montar_conjunto(tmp_path: Path, **gabaritos: dict) -> Path:
    """Escreve um conjunto em disco: uma entrada por gabarito nomeado."""

    (tmp_path / "emails").mkdir()
    (tmp_path / "gabaritos").mkdir()
    for nome, corpo in gabaritos.items():
        (tmp_path / "emails" / f"{nome}.txt").write_text("texto da demanda", encoding="utf-8")
        if corpo is not None:
            (tmp_path / "gabaritos" / f"{nome}.json").write_text(
                json.dumps(corpo), encoding="utf-8"
            )
    return tmp_path


class TestConjunto:
    def test_pareia_entrada_e_gabarito_pelo_nome(self, tmp_path: Path) -> None:
        raiz = montar_conjunto(tmp_path, caso_a=GABARITO_MINIMO)

        conjunto = carregar_conjunto(raiz)

        assert len(conjunto) == 1
        caso = conjunto.casos[0]
        assert caso.identificador == "caso_a"
        assert caso.canal == "emails"
        assert caso.texto == "texto da demanda"
        assert caso.esperado["carga_horaria"] == 16
        assert caso.sem_base == frozenset({"formato"})

    def test_com_base_e_o_complemento_de_sem_base(self, tmp_path: Path) -> None:
        raiz = montar_conjunto(tmp_path, caso_a=GABARITO_MINIMO)

        caso = carregar_conjunto(raiz).casos[0]

        assert "formato" not in caso.com_base
        assert "tema" in caso.com_base

    def test_entrada_sem_gabarito_fica_fora_da_medicao_mas_e_contada(self, tmp_path: Path) -> None:
        raiz = montar_conjunto(tmp_path, anotado=GABARITO_MINIMO, cru=None)

        conjunto = carregar_conjunto(raiz)

        assert len(conjunto) == 1
        assert conjunto.sem_gabarito == ("emails/cru.txt",)
        assert "1 entradas sem gabarito" in conjunto.resumo

    def test_separa_caso_real_de_sintetico(self, tmp_path: Path) -> None:
        real = GABARITO_MINIMO | {"procedencia": "real-anonimizado"}
        raiz = montar_conjunto(tmp_path, s=GABARITO_MINIMO, r=real)

        conjunto = carregar_conjunto(raiz)

        assert len(conjunto.por_procedencia(Procedencia.REAL)) == 1
        assert len(conjunto.por_procedencia(Procedencia.SINTETICO)) == 1
        assert "1 reais anonimizados, 1 sinteticos" in conjunto.resumo

    def test_conjunto_vazio_nao_e_erro(self, tmp_path: Path) -> None:
        assert len(carregar_conjunto(montar_conjunto(tmp_path))) == 0

    def test_recusa_json_invalido(self, tmp_path: Path) -> None:
        raiz = montar_conjunto(tmp_path, caso_a=GABARITO_MINIMO)
        (raiz / "gabaritos" / "caso_a.json").write_text("{nao e json", encoding="utf-8")

        with pytest.raises(ConjuntoInvalidoError, match="nao e JSON valido"):
            carregar_conjunto(raiz)

    def test_recusa_gabarito_sem_procedencia(self, tmp_path: Path) -> None:
        sem = {k: v for k, v in GABARITO_MINIMO.items() if k != "procedencia"}
        raiz = montar_conjunto(tmp_path, caso_a=sem)

        with pytest.raises(ConjuntoInvalidoError, match="procedencia"):
            carregar_conjunto(raiz)

    def test_recusa_chave_fora_do_contrato(self, tmp_path: Path) -> None:
        raiz = montar_conjunto(tmp_path, caso_a=GABARITO_MINIMO | {"extra": 1})

        with pytest.raises(ConjuntoInvalidoError, match="chave fora do contrato"):
            carregar_conjunto(raiz)

    def test_recusa_campo_que_a_saida_canonica_nao_tem(self, tmp_path: Path) -> None:
        raiz = montar_conjunto(tmp_path, caso_a=GABARITO_MINIMO | {"esperado": {"inventado": 1}})

        with pytest.raises(ConjuntoInvalidoError, match="nao tem"):
            carregar_conjunto(raiz)

    def test_recusa_campo_em_esperado_e_em_sem_base(self, tmp_path: Path) -> None:
        raiz = montar_conjunto(
            tmp_path,
            caso_a=GABARITO_MINIMO | {"esperado": {"tema": "x"}, "sem_base": ["tema"]},
        )

        with pytest.raises(ConjuntoInvalidoError, match="as duas coisas nao"):
            carregar_conjunto(raiz)

    def test_recusa_campo_gerado_em_sem_base(self, tmp_path: Path) -> None:
        """Gerar a ementa sem base literal no texto e o trabalho, nao alucinacao."""

        raiz = montar_conjunto(tmp_path, caso_a=GABARITO_MINIMO | {"sem_base": ["ementa"]})

        with pytest.raises(ConjuntoInvalidoError, match="campos gerados"):
            carregar_conjunto(raiz)

    def test_recusa_identificador_repetido_entre_canais(self, tmp_path: Path) -> None:
        raiz = montar_conjunto(tmp_path, caso_a=GABARITO_MINIMO)
        (raiz / "mensagens").mkdir()
        (raiz / "mensagens" / "caso_a.txt").write_text("outro", encoding="utf-8")

        with pytest.raises(ConjuntoInvalidoError, match="precisa ser unico"):
            carregar_conjunto(raiz)


ENTRADA_DE_CATALOGO = """
[[modelo]]
slug = "vendor/modelo-a"
apelido = "Modelo A"
justificativa = "referencia"
janela_de_contexto = 128000
usd_por_mtok_entrada = 1.0
usd_por_mtok_saida = 2.0
preco_consultado_em = 2026-10-16
"""


class TestCatalogo:
    def test_le_o_catalogo_versionado_do_repositorio(self) -> None:
        catalogo = carregar_catalogo()

        assert catalogo
        assert all(isinstance(m, ModeloCandidato) for m in catalogo)
        assert all(m.justificativa.strip() for m in catalogo), (
            "modelo sem justificativa nao e defensavel na banca"
        )

    def test_le_entrada_completa(self, tmp_path: Path) -> None:
        arquivo = tmp_path / "m.toml"
        arquivo.write_text(ENTRADA_DE_CATALOGO, encoding="utf-8")

        modelo = carregar_catalogo(arquivo)[0]

        assert modelo.slug == "vendor/modelo-a"
        assert modelo.preco_consultado_em == date(2026, 10, 16)
        assert not modelo.precos_pendentes
        assert modelo.custo_usd(1_000_000, 1_000_000) == pytest.approx(3.0)

    def test_preco_zero_e_sentinela_de_nao_consultado(self, tmp_path: Path) -> None:
        arquivo = tmp_path / "m.toml"
        arquivo.write_text(
            ENTRADA_DE_CATALOGO.replace("usd_por_mtok_entrada = 1.0", "usd_por_mtok_entrada = 0.0"),
            encoding="utf-8",
        )

        modelo = carregar_catalogo(arquivo)[0]

        assert modelo.precos_pendentes
        assert modelo.custo_usd(1000, 1000) is None, (
            "custo inventado e pior que custo ausente: parece medicao"
        )

    def test_recusa_arquivo_ausente(self, tmp_path: Path) -> None:
        with pytest.raises(CatalogoInvalidoError, match="nao encontrado"):
            carregar_catalogo(tmp_path / "nao-existe.toml")

    def test_recusa_catalogo_sem_modelo(self, tmp_path: Path) -> None:
        arquivo = tmp_path / "m.toml"
        arquivo.write_text("# vazio\n", encoding="utf-8")

        with pytest.raises(CatalogoInvalidoError, match="ao menos uma tabela"):
            carregar_catalogo(arquivo)

    def test_recusa_entrada_sem_chave_obrigatoria(self, tmp_path: Path) -> None:
        arquivo = tmp_path / "m.toml"
        arquivo.write_text(
            ENTRADA_DE_CATALOGO.replace('apelido = "Modelo A"\n', ""), encoding="utf-8"
        )

        with pytest.raises(CatalogoInvalidoError, match="falta"):
            carregar_catalogo(arquivo)

    def test_recusa_chave_desconhecida(self, tmp_path: Path) -> None:
        arquivo = tmp_path / "m.toml"
        arquivo.write_text(ENTRADA_DE_CATALOGO + 'extra = "x"\n', encoding="utf-8")

        with pytest.raises(CatalogoInvalidoError, match="chave desconhecida"):
            carregar_catalogo(arquivo)

    def test_recusa_data_de_preco_como_texto(self, tmp_path: Path) -> None:
        """Data entre aspas e texto, e preco sem data envelhece em silencio."""

        arquivo = tmp_path / "m.toml"
        arquivo.write_text(
            ENTRADA_DE_CATALOGO.replace(
                "preco_consultado_em = 2026-10-16", 'preco_consultado_em = "2026-10-16"'
            ),
            encoding="utf-8",
        )

        with pytest.raises(CatalogoInvalidoError, match="data TOML"):
            carregar_catalogo(arquivo)

    def test_recusa_slug_repetido(self, tmp_path: Path) -> None:
        arquivo = tmp_path / "m.toml"
        arquivo.write_text(ENTRADA_DE_CATALOGO * 2, encoding="utf-8")

        with pytest.raises(CatalogoInvalidoError, match="repetido"):
            carregar_catalogo(arquivo)

    def test_selecionar_sem_slug_devolve_o_catalogo_inteiro(self, tmp_path: Path) -> None:
        arquivo = tmp_path / "m.toml"
        arquivo.write_text(ENTRADA_DE_CATALOGO, encoding="utf-8")
        catalogo = carregar_catalogo(arquivo)

        assert selecionar(catalogo) == tuple(catalogo)

    def test_selecionar_recorta_e_respeita_a_ordem_pedida(self) -> None:
        catalogo = carregar_catalogo()
        pedidos = [catalogo[1].slug, catalogo[0].slug]

        assert [m.slug for m in selecionar(catalogo, pedidos)] == pedidos

    def test_selecionar_falha_cedo_com_slug_fora_do_catalogo(self) -> None:
        with pytest.raises(CatalogoInvalidoError, match="fora do catalogo"):
            selecionar(carregar_catalogo(), ["nao/existe"])
