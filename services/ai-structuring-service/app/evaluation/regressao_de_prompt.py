"""Regressao de acuracia entre versoes de prompt (RNF30, card #223).

O prompt de extracao e artefato versionado e faz parte do produto (RNF03): uma
mudanca de ``v2`` para ``v3`` pode reforcar uma regra e, sem querer, estragar
um campo que a versao anterior acertava. Sem teste que rode o gabarito contra
toda versao guardada no repositorio, essa regressao passa em silencio - ela so
aparece quando alguem nota, manualmente, que um numero caiu.

Este modulo fecha os quatro criterios do card:

1. ``comparar_versoes_de_prompt`` roda o conjunto de avaliacao uma vez por
   versao de prompt, reusando ``runner.executar`` (e, por tras dele,
   ``StructuringService.structure_course``) - a mesma execucao real que
   qualquer outra rodada de avaliacao deste modulo usa. Nao existe caminho
   paralelo que reimplemente a estruturacao so para medir.
2. ``ComparacaoDeVersoesDePrompt.por_campo`` devolve a acuracia de cada versao
   lado a lado, por campo.
3. ``ComparacaoDeVersoesDePrompt.regressoes`` e ``.reprova()`` aplicam o
   criterio de reprovacao: ver "Limiar de regressao" abaixo.
4. Esta docstring e a secao "Como rodar antes de promover uma versao" documentam
   o comando a executar.

Quais versoes entram na comparacao
-----------------------------------
``versoes_do_catalogo`` devolve, por padrao, **toda** versao de um prompt
presente em ``app/prompts/`` - ativa e ``substituido`` - porque o criterio de
aceite do card pede a comparacao "entre toda versao de prompt mantida no
repositorio", e e exatamente contra o historico que uma regressao faz sentido:
se ``v3`` piora um campo que ``v2`` acertava, o fato de ``v2`` estar
``substituido`` nao torna a regressao menos real. Quem quiser medir so a
versao ativa (por exemplo, para um numero de "estado atual" sem ruido de
historico) passa ``apenas_ativas=True``.

Limiar de regressao
--------------------
Uma versao mais nova reprova quando a acuracia de algum campo cai **mais de 5
pontos percentuais** (0.05) em relacao a qualquer versao mais antiga que tenha
medicao para aquele campo. Esse numero segue a mesma convencao ja usada neste
modulo de avaliacao: ``METAS`` em ``metrics.py`` trata diferenca de ate
alguns pontos percentuais como ruido de amostra pequena e so marca reprovacao
acima de uma folga; 5 p.p. e a folga que esse modulo ja reserva para "pequena
variacao, nao regressao" em metricas onde menor-e-melhor (``taxa_de_falha``:
meta 5%; ``taxa_de_alucinacao``: meta 5%). Usar 5 p.p. aqui tambem evita que o
conjunto de avaliacao ainda pequeno (poucos casos sinteticos, por enquanto -
ver ``app/evaluation/dataset.py``) dispare falso positivo por causa de um unico
caso que muda de lado: com N casos pequeno, um unico veredito trocado move a
acuracia de um campo por ``1/N`` - mais de 1 p.p. a cada caso perdido quando
N < 100 - e 5 p.p. absorve a oscilacao de um ou dois casos sem deixar passar
uma queda real.

Comparacao e feita apenas nos campos automatizaveis (``CAMPOS_AUTOMATICOS`` em
``metrics.py``: ``numero_participantes``, ``carga_horaria``, ``formato``) -
os mesmos que ``Medicao.acuracia_por_campo`` populam. Campo de julgamento
humano (``tema``, ``ementa`` etc.) nao tem numero automatico para comparar.

Como rodar antes de promover uma versao de prompt
----------------------------------------------------
Com o provedor mock (sem chave, sem rede) e o conjunto de avaliacao do
repositorio::

    import asyncio

    from app.evaluation.catalog import carregar_catalogo
    from app.evaluation.dataset import carregar_conjunto
    from app.evaluation.regressao_de_prompt import (
        comparar_versoes_de_prompt,
        versoes_do_catalogo,
    )
    from app.providers.mock_provider import MockLLMProvider


    async def main() -> None:
        conjunto = carregar_conjunto()
        modelo = carregar_catalogo()[0]
        comparacao = await comparar_versoes_de_prompt(
            nome_do_prompt="extract-requirements",
            versoes=versoes_do_catalogo("extract-requirements"),
            casos=conjunto.casos,
            modelo=modelo,
            fabrica_de_provedor=lambda slug, _settings: MockLLMProvider(model=slug),
        )
        for regressao in comparacao.regressoes:
            print(regressao)
        if comparacao.reprova():
            raise SystemExit("regressao de prompt encontrada - ver saida acima")


    asyncio.run(main())

Para o provedor real, troque a ``fabrica_de_provedor`` por
``app.providers.factory`` e informe ``settings``. Equivalente via teste
automatizado: ``pytest tests/unit/test_regressao_de_prompt.py -q`` roda a
mesma logica sobre cenarios fixos e falha se o criterio de regressao apontar
algo - e o jeito de travar isso no CI antes de promover uma versao nova a
``DEFAULT_PROMPT_VERSION``.
"""

from __future__ import annotations

import re
from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from typing import Final

from app.core.config import Settings
from app.evaluation.catalog import ModeloCandidato
from app.evaluation.dataset import CasoDeAvaliacao
from app.evaluation.metrics import CAMPOS_AUTOMATICOS, Medicao, medir
from app.evaluation.runner import FabricaDeProvedor, executar
from app.prompts import listar_prompts

#: Diferenca minima, em fracao (0.05 = 5 pontos percentuais), para uma queda de
#: acuracia entre versoes contar como regressao. Ver "Limiar de regressao" no
#: docstring do modulo para a justificativa do numero.
LIMIAR_DE_REGRESSAO: Final[float] = 0.05

_VERSAO_NUMERO: Final[re.Pattern[str]] = re.compile(r"^v([0-9]+)$")


def numero_da_versao(versao: str) -> int:
    """Extrai o inteiro de ``v<N>``, para ordenar por versao e nao por texto.

    Comparar a string ordenaria ``v10`` antes de ``v9`` - bug classico que essa
    funcao existe para evitar.

    Raises:
        ValueError: ``versao`` fora do formato ``v<N>``.
    """

    casamento = _VERSAO_NUMERO.match(versao)
    if casamento is None:
        raise ValueError(f"versao de prompt invalida: {versao!r} - use o formato 'v<N>'")
    return int(casamento.group(1))


def versoes_do_catalogo(nome_do_prompt: str, *, apenas_ativas: bool = False) -> tuple[str, ...]:
    """Versoes de ``nome_do_prompt`` no catalogo, da mais antiga para a mais nova.

    Args:
        nome_do_prompt: funcao do prompt, ex.: ``extract-requirements``.
        apenas_ativas: quando ``True``, exclui toda versao com
            ``status: substituido`` no proprio cabecalho do arquivo. Por
            padrao (``False``) inclui tambem o historico - ver "Quais versoes
            entram na comparacao" no docstring do modulo.

    Returns:
        Versoes (``"v1"``, ``"v2"``, ...) ordenadas por numero.
    """

    from app.prompts import carregar_prompt

    pares = [v for n, v in listar_prompts() if n == nome_do_prompt]
    if apenas_ativas:
        pares = [
            v
            for v in pares
            if carregar_prompt(nome_do_prompt, v).metadados.get("status") != "substituido"
        ]
    return tuple(sorted(pares, key=numero_da_versao))


@dataclass(frozen=True, slots=True)
class Regressao:
    """Uma queda de acuracia, em um campo, de uma versao antiga para uma nova.

    Attributes:
        campo: campo automatizavel afetado.
        versao_anterior: versao mais antiga usada como base de comparacao.
        versao_nova: versao mais nova que regrediu.
        acuracia_anterior: acuracia de ``versao_anterior`` naquele campo.
        acuracia_nova: acuracia de ``versao_nova`` naquele campo.
    """

    campo: str
    versao_anterior: str
    versao_nova: str
    acuracia_anterior: float
    acuracia_nova: float

    @property
    def queda(self) -> float:
        """Quantos pontos (em fracao) a acuracia caiu. Sempre positivo."""

        return self.acuracia_anterior - self.acuracia_nova

    def __str__(self) -> str:  # pragma: no cover - so para leitura em log/print
        return (
            f"{self.campo}: {self.versao_anterior} -> {self.versao_nova} "
            f"caiu {self.queda:.1%} ({self.acuracia_anterior:.1%} -> {self.acuracia_nova:.1%})"
        )


@dataclass(frozen=True, slots=True)
class ComparacaoDeVersoesDePrompt:
    """Resultado de medir o mesmo conjunto contra varias versoes de prompt.

    Attributes:
        medicoes: uma ``Medicao`` por versao, chaveada pela versao (``"v1"``,
            ``"v2"``, ...).
    """

    medicoes: Mapping[str, Medicao]

    @property
    def versoes_ordenadas(self) -> tuple[str, ...]:
        """Versoes medidas, da mais antiga para a mais nova."""

        return tuple(sorted(self.medicoes, key=numero_da_versao))

    def por_campo(self, campo: str) -> dict[str, float | None]:
        """Acuracia de cada versao naquele campo, na ordem de versao.

        ``None`` quando a versao nao tem medicao para o campo (gabarito sem
        anotacao para ele) - nunca zero, pelo mesmo motivo de
        ``Medicao.acuracia_por_campo``.
        """

        return {v: self.medicoes[v].acuracia_por_campo.get(campo) for v in self.versoes_ordenadas}

    @property
    def regressoes(self) -> tuple[Regressao, ...]:
        """Toda queda de acuracia acima de ``LIMIAR_DE_REGRESSAO``.

        Compara cada par (versao mais antiga, versao mais nova) - nao so
        versoes consecutivas - porque uma regressao introduzida em ``v2`` e
        nunca corrigida em ``v3`` ainda e uma regressao de ``v3`` em relacao a
        ``v1``, mesmo que ``v3`` nao tenha piorado nada em relacao a ``v2``.
        """

        versoes = self.versoes_ordenadas
        encontradas: list[Regressao] = []
        campos = sorted({c for m in self.medicoes.values() for c in m.acuracia_por_campo})

        for campo in campos:
            for indice, anterior in enumerate(versoes):
                acc_anterior = self.medicoes[anterior].acuracia_por_campo.get(campo)
                if acc_anterior is None:
                    continue
                for nova in versoes[indice + 1 :]:
                    acc_nova = self.medicoes[nova].acuracia_por_campo.get(campo)
                    if acc_nova is None:
                        continue
                    if acc_anterior - acc_nova > LIMIAR_DE_REGRESSAO:
                        encontradas.append(
                            Regressao(
                                campo=campo,
                                versao_anterior=anterior,
                                versao_nova=nova,
                                acuracia_anterior=acc_anterior,
                                acuracia_nova=acc_nova,
                            )
                        )
        return tuple(encontradas)

    def reprova(self) -> bool:
        """``True`` quando ha ao menos uma regressao - e o gate para o CI."""

        return bool(self.regressoes)


async def comparar_versoes_de_prompt(
    *,
    nome_do_prompt: str,
    versoes: Sequence[str],
    casos: Sequence[CasoDeAvaliacao],
    modelo: ModeloCandidato,
    fabrica_de_provedor: FabricaDeProvedor,
    settings: Settings | None = None,
) -> ComparacaoDeVersoesDePrompt:
    """Roda o conjunto de avaliacao uma vez por versao e compara a acuracia.

    Chama ``runner.executar`` (o mesmo caminho de execucao real usado por
    qualquer outra rodada de avaliacao) uma vez por versao em ``versoes``,
    fixando o modelo - a variavel sob teste aqui e o prompt, nao o modelo.

    Args:
        nome_do_prompt: funcao do prompt, ex.: ``extract-requirements``. So
            entra no relatorio; ``executar`` recebe a versao direto.
        versoes: versoes a comparar, ex.: ``versoes_do_catalogo(nome)``.
        casos: conjunto de avaliacao (``carregar_conjunto().casos``).
        modelo: modelo candidato fixo para todas as rodadas.
        fabrica_de_provedor: fabrica de provedor, como em ``runner.executar``
            - o provedor mock serve, nao exige rede nem chave.
        settings: configuracao do ambiente; por padrao, a configuracao padrao.

    Returns:
        ``ComparacaoDeVersoesDePrompt`` com uma ``Medicao`` por versao.
    """

    casos_por_id = {c.identificador: c for c in casos}
    medicoes: dict[str, Medicao] = {}

    for versao in versoes:
        rodada = await executar(
            casos=casos,
            modelos=[modelo],
            fabrica_de_provedor=fabrica_de_provedor,
            prompt_version=versao,
            settings=settings,
        )
        medicoes[versao] = medir(modelo.slug, casos_por_id, rodada.execucoes)

    return ComparacaoDeVersoesDePrompt(medicoes=medicoes)


__all__ = [
    "CAMPOS_AUTOMATICOS",
    "LIMIAR_DE_REGRESSAO",
    "ComparacaoDeVersoesDePrompt",
    "Regressao",
    "comparar_versoes_de_prompt",
    "numero_da_versao",
    "versoes_do_catalogo",
]
