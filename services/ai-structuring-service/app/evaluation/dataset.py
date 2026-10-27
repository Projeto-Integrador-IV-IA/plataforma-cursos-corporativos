"""Conjunto de avaliacao da estruturacao (RNF04).

Casos reais anonimizados do cliente, cada um com o texto bruto de entrada e o
gabarito anotado por um humano. E o que permite medir acuracia em vez de
opinar sobre a qualidade.

Regras:
    - dado de cliente sempre anonimizado antes de entrar no conjunto (RNF10);
    - o conjunto e versionado junto com o codigo, em tests/fixtures;
    - toda mudanca de prompt e reavaliada sobre o mesmo conjunto, senao os
      numeros nao sao comparaveis.

Meta minima: 20 casos anotados ate a 3a parcial (20/10).

Layout em disco, conforme ``tests/fixtures/README.md``::

    fixtures/
    |- emails/            corpo de e-mail colado
    |- transcricoes/      transcricao de reuniao
    |- mensagens/         conversas de WhatsApp
    |- gabaritos/         saida esperada de cada caso (JSON)

O pareamento e por nome de arquivo: ``emails/ec-001.txt`` casa com
``gabaritos/ec-001.json``. Entrada sem gabarito e caso nao anotado - fica fora
do conjunto de medicao, e o carregador diz quantos sao, para que a lacuna de
anotacao nunca passe em silencio.

**Procedencia e obrigatoria.** Cada gabarito declara ``procedencia`` como
``real-anonimizado`` ou ``sintetico``. Caso sintetico serve para exercitar o
arnes; nao sustenta numero reportavel. ``carregar_conjunto`` separa os dois, e
quem reporta metrica decide explicitamente o que usa - um numero de laboratorio
apresentado como medicao real seria pior que nenhum numero.
"""

from __future__ import annotations

import json
from collections.abc import Iterator, Mapping, Sequence
from dataclasses import dataclass, field
from enum import StrEnum
from pathlib import Path
from typing import Any, Final

from app.domain.course import CAMPOS_GERADOS, CAMPOS_INFERIVEIS

#: Diretorios de entrada, na ordem em que sao varridos.
PASTAS_DE_ENTRADA: Final[tuple[str, ...]] = ("emails", "transcricoes", "mensagens")

#: Pasta dos gabaritos anotados.
PASTA_DE_GABARITOS: Final[str] = "gabaritos"

#: Extensao aceita para o texto de entrada.
SUFIXO_DE_ENTRADA: Final[str] = ".txt"


class Procedencia(StrEnum):
    """Origem do caso. Decide se o numero medido sobre ele e reportavel."""

    REAL = "real-anonimizado"
    SINTETICO = "sintetico"


class ConjuntoInvalidoError(Exception):
    """Gabarito malformado. Falha na leitura, nunca no meio de uma medicao."""


@dataclass(frozen=True, slots=True)
class CasoDeAvaliacao:
    """Um par entrada/gabarito do conjunto.

    Attributes:
        identificador: nome do arquivo sem extensao, unico no conjunto.
        canal: pasta de origem (``emails``, ``transcricoes``, ``mensagens``).
        procedencia: real anonimizado ou sintetico.
        texto: demanda bruta, como chegou.
        esperado: valor correto por campo, anotado por humano. So traz campo
            cuja informacao existe no texto.
        sem_base: campos cuja informacao **nao** esta no texto. Preencher
            qualquer um deles e alucinacao; declara-los ausentes e acerto.
        observacoes: nota do anotador, livre.
    """

    identificador: str
    canal: str
    procedencia: Procedencia
    texto: str
    esperado: Mapping[str, Any]
    sem_base: frozenset[str]
    observacoes: str | None = None

    @property
    def com_base(self) -> frozenset[str]:
        """Campos inferiveis cuja informacao existe no texto."""

        return frozenset(CAMPOS_INFERIVEIS) - self.sem_base


@dataclass(frozen=True, slots=True)
class Conjunto:
    """Conjunto carregado, com a contabilidade da anotacao a vista.

    Attributes:
        casos: casos anotados, em ordem de identificador.
        sem_gabarito: entradas encontradas sem gabarito correspondente.
    """

    casos: Sequence[CasoDeAvaliacao] = field(default_factory=tuple)
    sem_gabarito: Sequence[str] = field(default_factory=tuple)

    def __len__(self) -> int:
        return len(self.casos)

    def __iter__(self) -> Iterator[CasoDeAvaliacao]:
        return iter(self.casos)

    def por_procedencia(self, procedencia: Procedencia) -> tuple[CasoDeAvaliacao, ...]:
        """Casos de uma procedencia so.

        Reportar metrica exige escolher: ``Procedencia.REAL`` sustenta numero de
        entrega, ``Procedencia.SINTETICO`` so serve para exercitar o arnes.
        """

        return tuple(c for c in self.casos if c.procedencia is procedencia)

    @property
    def resumo(self) -> str:
        """Uma linha com o estado da anotacao, para abrir qualquer relatorio."""

        reais = len(self.por_procedencia(Procedencia.REAL))
        sinteticos = len(self.por_procedencia(Procedencia.SINTETICO))
        pendentes = len(self.sem_gabarito)
        return (
            f"{len(self.casos)} casos anotados "
            f"({reais} reais anonimizados, {sinteticos} sinteticos); "
            f"{pendentes} entradas sem gabarito"
        )


def raiz_padrao() -> Path:
    """``tests/fixtures`` na raiz do repositorio, a partir deste arquivo."""

    return Path(__file__).resolve().parents[4] / "tests" / "fixtures"


def carregar_conjunto(raiz: Path | None = None) -> Conjunto:
    """Le o conjunto de avaliacao do disco.

    Args:
        raiz: diretorio de fixtures; por padrao ``tests/fixtures``.

    Returns:
        Conjunto com os casos anotados e a lista de entradas sem gabarito.

    Raises:
        ConjuntoInvalidoError: gabarito ilegivel, sem procedencia declarada, com
            campo desconhecido, ou identificador repetido entre canais.
    """

    base = raiz or raiz_padrao()
    gabaritos = base / PASTA_DE_GABARITOS

    casos: list[CasoDeAvaliacao] = []
    pendentes: list[str] = []
    vistos: dict[str, str] = {}

    for pasta in PASTAS_DE_ENTRADA:
        diretorio = base / pasta
        if not diretorio.is_dir():
            continue
        for entrada in sorted(diretorio.glob(f"*{SUFIXO_DE_ENTRADA}")):
            ident = entrada.stem
            if ident in vistos:
                raise ConjuntoInvalidoError(
                    f"identificador {ident!r} aparece em {vistos[ident]!r} e em {pasta!r}; "
                    "o nome e a chave do pareamento com o gabarito e precisa ser unico"
                )
            vistos[ident] = pasta

            anotacao = gabaritos / f"{ident}.json"
            if not anotacao.is_file():
                pendentes.append(f"{pasta}/{entrada.name}")
                continue

            casos.append(
                _montar_caso(
                    identificador=ident,
                    canal=pasta,
                    texto=entrada.read_text(encoding="utf-8"),
                    anotacao=anotacao,
                )
            )

    return Conjunto(
        casos=tuple(sorted(casos, key=lambda c: c.identificador)),
        sem_gabarito=tuple(pendentes),
    )


def _montar_caso(*, identificador: str, canal: str, texto: str, anotacao: Path) -> CasoDeAvaliacao:
    """Valida e converte um gabarito em ``CasoDeAvaliacao``."""

    try:
        bruto = json.loads(anotacao.read_text(encoding="utf-8"))
    except json.JSONDecodeError as erro:
        raise ConjuntoInvalidoError(f"gabarito {anotacao.name} nao e JSON valido: {erro}") from erro

    if not isinstance(bruto, dict):
        raise ConjuntoInvalidoError(f"gabarito {anotacao.name} precisa ser um objeto JSON")

    desconhecidas = set(bruto) - {"procedencia", "esperado", "sem_base", "observacoes"}
    if desconhecidas:
        raise ConjuntoInvalidoError(
            f"gabarito {anotacao.name} tem chave fora do contrato: {sorted(desconhecidas)}"
        )

    try:
        procedencia = Procedencia(bruto.get("procedencia", ""))
    except ValueError as erro:
        aceitas = ", ".join(p.value for p in Procedencia)
        raise ConjuntoInvalidoError(
            f"gabarito {anotacao.name} precisa declarar procedencia ({aceitas}): "
            "numero medido sobre caso sintetico nao e reportavel como medicao real"
        ) from erro

    esperado = bruto.get("esperado") or {}
    if not isinstance(esperado, dict):
        raise ConjuntoInvalidoError(f"gabarito {anotacao.name}: 'esperado' precisa ser objeto")

    sem_base = bruto.get("sem_base") or []
    if not isinstance(sem_base, list) or not all(isinstance(c, str) for c in sem_base):
        raise ConjuntoInvalidoError(
            f"gabarito {anotacao.name}: 'sem_base' precisa ser lista de texto"
        )

    conhecidos = set(CAMPOS_INFERIVEIS)
    fora = (set(esperado) | set(sem_base)) - conhecidos
    if fora:
        raise ConjuntoInvalidoError(
            f"gabarito {anotacao.name} cita campo que a saida canonica nao tem: {sorted(fora)}"
        )

    conflito = set(esperado) & set(sem_base)
    if conflito:
        raise ConjuntoInvalidoError(
            f"gabarito {anotacao.name}: {sorted(conflito)} esta em 'esperado' e em 'sem_base'. "
            "Um campo tem base no texto ou nao tem; as duas coisas nao."
        )

    gerados_sem_base = set(sem_base) & set(CAMPOS_GERADOS)
    if gerados_sem_base:
        raise ConjuntoInvalidoError(
            f"gabarito {anotacao.name}: {sorted(gerados_sem_base)} sao campos gerados e nao "
            "podem entrar em 'sem_base'. A ementa e os objetivos sao produzidos a partir dos "
            "requisitos, nao copiados do texto - trata-los como 'sem base' contaria a geracao "
            "correta como alucinacao."
        )

    return CasoDeAvaliacao(
        identificador=identificador,
        canal=canal,
        procedencia=procedencia,
        texto=texto,
        esperado=dict(esperado),
        sem_base=frozenset(sem_base),
        observacoes=bruto.get("observacoes"),
    )
