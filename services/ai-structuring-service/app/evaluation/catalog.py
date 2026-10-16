"""Catalogo de modelos candidatos a avaliacao (RNF04, card #216).

Comparar modelos exige decidir quais entram na disputa e registrar isso de forma
reproduzivel. Sem catalogo versionado o resultado nao e defensavel: ninguem
consegue repetir a medicao, e preco de API muda sem avisar.

O catalogo e um arquivo TOML versionado ao lado deste modulo
(``modelos.toml``), nunca variavel de ambiente - o ambiente guarda segredo
(RNF11), nao decisao de projeto.

Cada entrada declara, por modelo:
    slug                identificador no provedor, como vai no payload
    apelido             nome curto para tabela e grafico
    justificativa       por que este modelo entra na disputa
    janela_de_contexto  tokens de entrada que o modelo aceita
    usd_por_mtok_*      preco de entrada e de saida, por milhao de tokens
    preco_consultado_em data da consulta de preco

O preco e declarado com data de proposito: numero de custo sem data envelhece
em silencio, e foi exatamente o problema apontado na revisao do levantamento de
custos (card #121).
"""

from __future__ import annotations

import tomllib
from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from datetime import date
from pathlib import Path
from typing import Any, Final

#: Arquivo do catalogo, versionado junto com o codigo.
CAMINHO_PADRAO: Final[Path] = Path(__file__).with_name("modelos.toml")

#: Chaves obrigatorias em cada entrada.
_OBRIGATORIAS: Final[frozenset[str]] = frozenset(
    {
        "slug",
        "apelido",
        "justificativa",
        "janela_de_contexto",
        "usd_por_mtok_entrada",
        "usd_por_mtok_saida",
        "preco_consultado_em",
    }
)


class CatalogoInvalidoError(Exception):
    """Catalogo malformado. Falha na leitura, nunca no meio de uma avaliacao."""


@dataclass(frozen=True, slots=True)
class ModeloCandidato:
    """Um modelo inscrito na avaliacao."""

    slug: str
    apelido: str
    justificativa: str
    janela_de_contexto: int
    usd_por_mtok_entrada: float
    usd_por_mtok_saida: float
    preco_consultado_em: date

    @property
    def precos_pendentes(self) -> bool:
        """Preco ainda nao consultado no provedor.

        Zero e sentinela de "nao consultado", nao de "gratuito". Quem reporta
        custo precisa checar isto antes: numero de custo inventado e pior que
        custo ausente, porque parece medicao.
        """

        return self.usd_por_mtok_entrada <= 0 or self.usd_por_mtok_saida <= 0

    def custo_usd(self, tokens_entrada: int, tokens_saida: int) -> float | None:
        """Custo de uma chamada, pelos precos declarados no catalogo.

        Returns:
            ``None`` quando o preco deste modelo ainda nao foi consultado.
        """

        if self.precos_pendentes:
            return None
        entrada = tokens_entrada / 1_000_000 * self.usd_por_mtok_entrada
        saida = tokens_saida / 1_000_000 * self.usd_por_mtok_saida
        return entrada + saida


def carregar_catalogo(caminho: Path | None = None) -> tuple[ModeloCandidato, ...]:
    """Le o catalogo de modelos do disco.

    Args:
        caminho: arquivo TOML; por padrao ``modelos.toml`` ao lado deste modulo.

    Returns:
        Modelos candidatos, na ordem declarada no arquivo.

    Raises:
        CatalogoInvalidoError: arquivo ausente, TOML ilegivel, entrada sem chave
            obrigatoria, chave desconhecida, ou slug repetido.
    """

    arquivo = caminho or CAMINHO_PADRAO
    if not arquivo.is_file():
        raise CatalogoInvalidoError(f"catalogo nao encontrado em {arquivo}")

    try:
        bruto = tomllib.loads(arquivo.read_text(encoding="utf-8"))
    except tomllib.TOMLDecodeError as erro:
        raise CatalogoInvalidoError(f"catalogo {arquivo.name} nao e TOML valido: {erro}") from erro

    entradas = bruto.get("modelo")
    if not isinstance(entradas, list) or not entradas:
        raise CatalogoInvalidoError(
            f"catalogo {arquivo.name} precisa de ao menos uma tabela [[modelo]]"
        )

    modelos: list[ModeloCandidato] = []
    slugs: set[str] = set()
    for i, entrada in enumerate(entradas, 1):
        modelo = _montar(entrada, posicao=i, arquivo=arquivo.name)
        if modelo.slug in slugs:
            raise CatalogoInvalidoError(f"catalogo {arquivo.name}: slug {modelo.slug!r} repetido")
        slugs.add(modelo.slug)
        modelos.append(modelo)
    return tuple(modelos)


def selecionar(
    catalogo: Sequence[ModeloCandidato], slugs: Sequence[str] | None = None
) -> tuple[ModeloCandidato, ...]:
    """Recorta o catalogo para um subconjunto de slugs.

    Rodar sobre um subconjunto e o que permite iterar sem gastar credito em
    todos os modelos.

    Raises:
        CatalogoInvalidoError: algum slug pedido nao esta no catalogo.
    """

    if not slugs:
        return tuple(catalogo)
    por_slug: Mapping[str, ModeloCandidato] = {m.slug: m for m in catalogo}
    faltando = [s for s in slugs if s not in por_slug]
    if faltando:
        disponiveis = ", ".join(sorted(por_slug))
        raise CatalogoInvalidoError(
            f"slug fora do catalogo: {faltando}. Disponiveis: {disponiveis}."
        )
    return tuple(por_slug[s] for s in slugs)


def _montar(entrada: Any, *, posicao: int, arquivo: str) -> ModeloCandidato:
    """Valida uma entrada do catalogo."""

    if not isinstance(entrada, dict):
        raise CatalogoInvalidoError(f"catalogo {arquivo}: entrada {posicao} nao e tabela")

    faltando = _OBRIGATORIAS - set(entrada)
    if faltando:
        raise CatalogoInvalidoError(
            f"catalogo {arquivo}, entrada {posicao}: falta {sorted(faltando)}"
        )
    sobrando = set(entrada) - _OBRIGATORIAS
    if sobrando:
        raise CatalogoInvalidoError(
            f"catalogo {arquivo}, entrada {posicao}: chave desconhecida {sorted(sobrando)}"
        )

    consultado = entrada["preco_consultado_em"]
    if not isinstance(consultado, date):
        raise CatalogoInvalidoError(
            f"catalogo {arquivo}, entrada {posicao}: 'preco_consultado_em' precisa ser "
            "data TOML sem aspas (AAAA-MM-DD) - preco sem data envelhece em silencio"
        )

    try:
        return ModeloCandidato(
            slug=str(entrada["slug"]),
            apelido=str(entrada["apelido"]),
            justificativa=str(entrada["justificativa"]),
            janela_de_contexto=int(entrada["janela_de_contexto"]),
            usd_por_mtok_entrada=float(entrada["usd_por_mtok_entrada"]),
            usd_por_mtok_saida=float(entrada["usd_por_mtok_saida"]),
            preco_consultado_em=consultado,
        )
    except (TypeError, ValueError) as erro:
        raise CatalogoInvalidoError(
            f"catalogo {arquivo}, entrada {posicao}: valor fora do tipo esperado ({erro})"
        ) from erro
