"""Similaridade de cosseno entre embeddings (RNF28 consolidado, card #159).

Calculo em Python, nao via operador nativo do pgvector (``<=>``): o unico
outro dialeto que este servico testa e o SQLite (sem tipo vetorial nem
operador de distancia), e um metodo so, exercitado pelos dois dialetos,
evita que o caminho testado em CI divirja do caminho real em produção. No
volume de um MVP (poucos trechos por demanda), a comparacao em Python contra
o conjunto ja filtrado por demanda e imediata; o indice ``hnsw`` criado pela
migration do card #158 fica disponivel para quando o volume justificar trocar
este calculo por uma consulta nativa.
"""

import math
from collections.abc import Sequence


def cosseno(a: Sequence[float], b: Sequence[float]) -> float:
    """Similaridade de cosseno entre dois vetores da mesma dimensao.

    1.0 para vetores idênticos em direcao, 0.0 para ortogonais, -1.0 para
    opostos. Vetor nulo (todo zero) devolve 0.0 em vez de dividir por zero -
    nao ha direcao a comparar.

    Raises:
        ValueError: os vetores tem dimensoes diferentes.
    """

    if len(a) != len(b):
        raise ValueError(f"vetores de dimensoes diferentes: {len(a)} e {len(b)}")

    produto_escalar = sum(x * y for x, y in zip(a, b, strict=True))
    norma_a = math.sqrt(sum(x * x for x in a))
    norma_b = math.sqrt(sum(y * y for y in b))
    if norma_a == 0.0 or norma_b == 0.0:
        return 0.0
    return produto_escalar / (norma_a * norma_b)
