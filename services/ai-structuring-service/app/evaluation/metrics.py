"""Metricas de qualidade da estruturacao (RNF04).

Sao o entregavel verificavel da 3a parcial (20/10). Sem definicao explicita do
que se mede, a entrega nao tem como ser avaliada - ver
docs/04-ia/metricas-qualidade.md, que e a especificacao que este modulo
implementa.

O que este modulo calcula sozinho e o que nao calcula
-----------------------------------------------------
O documento de metricas fixa o criterio de comparacao por tipo de campo, e um
deles **nao e automatizavel**:

    numero_participantes, carga_horaria   igualdade exata
    formato                               vocabulario fechado, igualdade exata
    tema, nicho, publico_alvo             equivalencia semantica, julgada por
                                          dois humanos
    objetivos_aprendizagem, ementa        escala 1-5, avaliacao humana (RF12)

Campo de texto livre comparado por igualdade de string produziria acuracia
artificialmente baixa - "treinamento de lideranca para coordenadores" e
"lideranca para coordenadores recem-promovidos" descrevem o mesmo tema e
falhariam. Por isso estes campos ficam **fora** do numero automatico e saem
listados como pendentes de julgamento, em vez de entrar silenciosamente na
media. ``Medicao.pendentes_de_julgamento`` existe para esse recorte nao se
perder no relatorio.

Denominador da taxa de alucinacao
---------------------------------
O documento diz "proporcao de campos preenchidos sem base no texto" sem fixar o
denominador. Aqui e **sobre os campos sem base declarados no gabarito**: de tudo
que o modelo nao tinha como saber, quanto ele preencheu de todo jeito. Essa
leitura mantem a metrica comparavel entre casos com quantidade diferente de
lacuna, e e o contrapeso direto do reconhecimento de ausencia, que tem o mesmo
denominador.

Cobertura de evidencia (RNF27, card #157)
------------------------------------------
``cobertura_de_evidencia`` mede, entre os campos preenchidos, quantos citam ao
menos um trecho em ``evidencias``. Para uma execucao que passou pela validacao
do dominio, o numero tende a 100%: o schema ja recusa campo preenchido sem
citacao e citacao que nao corresponde a um trecho real (cards #153-#156), e
``curso`` so chega aqui depois de aprovado. O numero continua sendo o que vale
reportar - ele confirma que a barreira funciona -, mas quem le o relatorio
precisa saber que **nao e** uma medida de qualidade da citacao em si, so da
sua presenca apos o gate. ``taxa_de_citacao_invalida`` e o complemento: conta,
entre todas as execucoes do modelo (inclusive as recusadas), quantas falharam
especificamente por citar um trecho inexistente - identificada por um trecho
fixo da mensagem de erro (``_MARCA_DE_CITACAO_INVALIDA``), unico jeito
disponivel de distinguir essa causa das demais depois que ``runner.py``
converte a excecao em texto.
"""

from __future__ import annotations

import statistics
from collections.abc import Mapping, Sequence
from dataclasses import dataclass, field
from enum import StrEnum
from typing import Any, Final

from app.domain.course import (
    CAMPOS_EXTRAIDOS,
    CAMPOS_GERADOS,
    CAMPOS_INFERIVEIS,
    CourseFormat,
    StructuredCourse,
)
from app.evaluation.dataset import CasoDeAvaliacao


class Criterio(StrEnum):
    """Como o valor de um campo e comparado com o gabarito."""

    EXATO = "exato"
    VOCABULARIO_FECHADO = "vocabulario-fechado"
    HUMANO = "humano"


#: Criterio de comparacao por campo, conforme docs/04-ia/metricas-qualidade.md.
CRITERIO_POR_CAMPO: Final[Mapping[str, Criterio]] = {
    "tema": Criterio.HUMANO,
    "nicho": Criterio.HUMANO,
    "publico_alvo": Criterio.HUMANO,
    "numero_participantes": Criterio.EXATO,
    "carga_horaria": Criterio.EXATO,
    "formato": Criterio.VOCABULARIO_FECHADO,
    "objetivos_aprendizagem": Criterio.HUMANO,
    "ementa": Criterio.HUMANO,
}

#: Campos que entram no numero automatico.
CAMPOS_AUTOMATICOS: Final[tuple[str, ...]] = tuple(
    c for c in CAMPOS_INFERIVEIS if CRITERIO_POR_CAMPO[c] is not Criterio.HUMANO
)

#: Campos que dependem de julgamento humano e ficam fora da media automatica.
CAMPOS_DE_JULGAMENTO: Final[tuple[str, ...]] = tuple(
    c for c in CAMPOS_INFERIVEIS if CRITERIO_POR_CAMPO[c] is Criterio.HUMANO
)

#: Campos essenciais, com meta propria de 80% no documento de metricas.
CAMPOS_ESSENCIAIS: Final[tuple[str, ...]] = ("tema", "publico_alvo", "carga_horaria")

#: Metas iniciais declaradas em docs/04-ia/metricas-qualidade.md.
METAS: Final[Mapping[str, float]] = {
    "acuracia_essenciais": 0.80,
    "acuracia_global": 0.75,
    "cobertura": 0.85,
    "taxa_de_alucinacao": 0.05,
    "reconhecimento_de_ausencia": 0.90,
    "estabilidade": 0.90,
    "conformidade_de_schema": 0.95,
    "taxa_de_falha": 0.05,
    "cobertura_de_evidencia": 0.95,
    "taxa_de_citacao_invalida": 0.05,
}

#: Trecho da mensagem de ``LLMInvalidResponseError`` que distingue citacao
#: forjada (card #156) de resposta fora do schema - as duas chegam aqui como
#: o mesmo ``erro`` de texto, e e so pelo conteudo da mensagem que se separam.
_MARCA_DE_CITACAO_INVALIDA: Final[str] = "cita trecho que nao foi enviado"


@dataclass(frozen=True, slots=True)
class Execucao:
    """Uma chamada ao modelo sobre um caso do conjunto.

    Attributes:
        caso: identificador do caso avaliado.
        modelo: slug do catalogo, que e a chave de agrupamento da medicao.
        modelo_reportado: modelo que o provedor diz ter atendido a chamada.
            Guardado separado de proposito: roteador como o OpenRouter pode
            servir um modelo diferente do pedido, e agrupar pelo reportado
            quebraria o vinculo com o catalogo. Divergencia entre os dois e
            achado, nao detalhe.
        curso: saida validada; ``None`` quando a resposta nao passou no schema.
        valida_de_primeira: a primeira tentativa ja passou no schema.
        tentativas: quantas chamadas foram necessarias.
        latencia_ms: tempo de ponta a ponta da execucao.
        tokens_entrada: tokens cobrados na entrada.
        tokens_saida: tokens cobrados na saida.
        erro: causa da falha, quando houve.
    """

    caso: str
    modelo: str
    modelo_reportado: str | None = None
    curso: StructuredCourse | None = None
    valida_de_primeira: bool = False
    tentativas: int = 1
    latencia_ms: float | None = None
    tokens_entrada: int | None = None
    tokens_saida: int | None = None
    erro: str | None = None

    @property
    def falhou(self) -> bool:
        return self.curso is None


@dataclass(frozen=True, slots=True)
class Medicao:
    """Resultado agregado de um modelo sobre o conjunto.

    ``None`` significa "sem base para calcular", nunca zero: conjunto sem campo
    sem base nao tem taxa de alucinacao, e reportar 0% nesse caso afirmaria algo
    que nao foi medido.
    """

    modelo: str
    casos: int
    acuracia_por_campo: Mapping[str, float | None] = field(default_factory=dict)
    acuracia_essenciais: float | None = None
    acuracia_global: float | None = None
    cobertura: float | None = None
    taxa_de_alucinacao: float | None = None
    reconhecimento_de_ausencia: float | None = None
    conformidade_de_schema: float | None = None
    taxa_de_falha: float | None = None
    cobertura_de_evidencia_por_campo: Mapping[str, float | None] = field(default_factory=dict)
    cobertura_de_evidencia: float | None = None
    taxa_de_citacao_invalida: float | None = None
    latencia_p50_ms: float | None = None
    latencia_p95_ms: float | None = None
    tokens_por_demanda: float | None = None
    pendentes_de_julgamento: Sequence[str] = field(default_factory=tuple)

    def atende(self, metrica: str) -> bool | None:
        """Compara a metrica com a meta do documento.

        Returns:
            ``None`` quando a metrica nao foi medida. Para as taxas (de
            alucinacao, de falha, de citacao invalida), menor e melhor; nas
            demais, maior.
        """

        valor = getattr(self, metrica, None)
        meta = METAS.get(metrica)
        if valor is None or meta is None:
            return None
        if metrica in ("taxa_de_alucinacao", "taxa_de_falha", "taxa_de_citacao_invalida"):
            return valor <= meta
        return valor >= meta


def comparar(campo: str, esperado: Any, obtido: Any) -> bool | None:
    """Compara um valor com o gabarito, pelo criterio do campo.

    Returns:
        ``None`` para campo de julgamento humano - nao ha o que decidir aqui.
    """

    criterio = CRITERIO_POR_CAMPO.get(campo, Criterio.HUMANO)
    if criterio is Criterio.HUMANO:
        return None
    if criterio is Criterio.VOCABULARIO_FECHADO:
        return _normalizar_formato(esperado) == _normalizar_formato(obtido)
    return esperado == obtido


def _normalizar_formato(valor: Any) -> str | None:
    """Reduz o formato ao vocabulario fechado de ``CourseFormat``."""

    if valor is None:
        return None
    texto = str(valor.value if isinstance(valor, CourseFormat) else valor).strip().casefold()
    return texto or None


def _preenchido(campo: str, curso: StructuredCourse) -> bool:
    """O modelo entregou valor para este campo?

    Lista vazia e ``None`` sao ausencia declarada, nao valor.
    """

    valor = getattr(curso, campo, None)
    if valor is None:
        return False
    if campo in CAMPOS_GERADOS:
        return bool(valor)
    return True


def _declarado_ausente(campo: str, curso: StructuredCourse) -> bool:
    """O modelo declarou este campo em ``campos_ausentes``?"""

    return any(lacuna.campo == campo for lacuna in curso.campos_ausentes)


def medir(
    modelo: str,
    casos: Mapping[str, CasoDeAvaliacao],
    execucoes: Sequence[Execucao],
) -> Medicao:
    """Agrega as execucoes de um modelo nas metricas do documento.

    Args:
        modelo: slug do modelo medido.
        casos: conjunto de avaliacao, indexado por identificador.
        execucoes: execucoes daquele modelo, uma por caso.

    Returns:
        Medicao com as metricas automatizaveis e a lista do que ficou pendente
        de julgamento humano.
    """

    minhas = [e for e in execucoes if e.modelo == modelo]
    if not minhas:
        return Medicao(modelo=modelo, casos=0, pendentes_de_julgamento=CAMPOS_DE_JULGAMENTO)

    acertos: dict[str, list[bool]] = {c: [] for c in CAMPOS_AUTOMATICOS}
    com_evidencia: dict[str, list[bool]] = {c: [] for c in CAMPOS_INFERIVEIS}
    com_base_total = com_base_preenchido = 0
    sem_base_total = sem_base_preenchido = sem_base_declarado = 0

    for execucao in minhas:
        caso = casos.get(execucao.caso)
        if caso is None or execucao.curso is None:
            continue
        curso = execucao.curso

        for campo in CAMPOS_AUTOMATICOS:
            if campo in caso.esperado:
                veredito = comparar(campo, caso.esperado[campo], getattr(curso, campo, None))
                if veredito is not None:
                    acertos[campo].append(veredito)

        for campo in caso.com_base:
            com_base_total += 1
            com_base_preenchido += int(_preenchido(campo, curso))

        for campo in caso.sem_base:
            sem_base_total += 1
            sem_base_preenchido += int(_preenchido(campo, curso))
            sem_base_declarado += int(_declarado_ausente(campo, curso))

        for campo in CAMPOS_INFERIVEIS:
            if _preenchido(campo, curso):
                com_evidencia[campo].append(bool(curso.evidencias.get(campo)))

    por_campo = {c: (_media(v) if v else None) for c, v in acertos.items()}
    automaticos = [v for v in por_campo.values() if v is not None]
    essenciais = [por_campo[c] for c in CAMPOS_ESSENCIAIS if por_campo.get(c) is not None]
    latencias = [e.latencia_ms for e in minhas if e.latencia_ms is not None]
    tokens = [
        (e.tokens_entrada or 0) + (e.tokens_saida or 0)
        for e in minhas
        if e.tokens_entrada is not None or e.tokens_saida is not None
    ]
    cobertura_por_campo = {c: (_media(v) if v else None) for c, v in com_evidencia.items()}
    todas_as_citacoes = [v for valores in com_evidencia.values() for v in valores]
    citacoes_invalidas = sum(
        1 for e in minhas if e.erro is not None and _MARCA_DE_CITACAO_INVALIDA in e.erro
    )

    return Medicao(
        modelo=modelo,
        casos=len(minhas),
        acuracia_por_campo=por_campo,
        acuracia_essenciais=_media(essenciais) if essenciais else None,
        acuracia_global=_media(automaticos) if automaticos else None,
        cobertura=_razao(com_base_preenchido, com_base_total),
        taxa_de_alucinacao=_razao(sem_base_preenchido, sem_base_total),
        reconhecimento_de_ausencia=_razao(sem_base_declarado, sem_base_total),
        conformidade_de_schema=_razao(sum(e.valida_de_primeira for e in minhas), len(minhas)),
        taxa_de_falha=_razao(sum(e.falhou for e in minhas), len(minhas)),
        cobertura_de_evidencia_por_campo=cobertura_por_campo,
        cobertura_de_evidencia=_media(todas_as_citacoes) if todas_as_citacoes else None,
        taxa_de_citacao_invalida=_razao(citacoes_invalidas, len(minhas)),
        latencia_p50_ms=_percentil(latencias, 50),
        latencia_p95_ms=_percentil(latencias, 95),
        tokens_por_demanda=_media(tokens) if tokens else None,
        pendentes_de_julgamento=CAMPOS_DE_JULGAMENTO,
    )


def estabilidade(execucoes: Sequence[Execucao]) -> float | None:
    """Proporcao de campos extraidos identicos em todas as repeticoes (RNF03).

    Espera varias execucoes do **mesmo** modelo sobre o **mesmo** caso. Com
    menos de duas repeticoes nao ha o que comparar e devolve ``None``.
    """

    validas = [e for e in execucoes if e.curso is not None]
    if len(validas) < 2:
        return None

    estaveis = 0
    for campo in CAMPOS_EXTRAIDOS:
        valores = {_chave_comparavel(getattr(e.curso, campo, None)) for e in validas}
        estaveis += int(len(valores) == 1)
    return _razao(estaveis, len(CAMPOS_EXTRAIDOS))


def _chave_comparavel(valor: Any) -> Any:
    """Torna o valor hashavel para comparar repeticoes."""

    if isinstance(valor, list):
        return tuple(_chave_comparavel(v) for v in valor)
    if hasattr(valor, "model_dump"):
        return repr(valor.model_dump())
    return valor


def _media(valores: Sequence[float] | Sequence[bool]) -> float:
    return statistics.fmean(float(v) for v in valores)


def _razao(parte: int, total: int) -> float | None:
    return parte / total if total else None


def _percentil(valores: Sequence[float], p: int) -> float | None:
    """Percentil por interpolacao linear, sem dependencia externa."""

    if not valores:
        return None
    ordenados = sorted(valores)
    if len(ordenados) == 1:
        return ordenados[0]
    posicao = (len(ordenados) - 1) * (p / 100)
    baixo = int(posicao)
    alto = min(baixo + 1, len(ordenados) - 1)
    peso = posicao - baixo
    return ordenados[baixo] * (1 - peso) + ordenados[alto] * peso
