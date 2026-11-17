"""Provedor de embedding falso, para desenvolvimento e testes (RF29, RNF12).

Mesma razao do ``MockLLMProvider``: roda a CI sem baixar modelo nem rede, e
devolve vetor deterministico - o mesmo texto sempre vira o mesmo vetor, e
textos diferentes viram vetores diferentes, o suficiente para testar busca
por similaridade sem depender de semantica de verdade.

Selecionado por ``EMBEDDING_PROVIDER=mock`` - o padrao em desenvolvimento e o
unico usado na CI.
"""

import hashlib
import time
from typing import ClassVar

from app.providers.embedding_base import EmbeddingProvider, EmbeddingResult

#: Mesma dimensao do provedor real (``sentence-transformers/all-MiniLM-L6-v2``),
#: para que um teste trocar de provedor mock para o de verdade nao mude o
#: tamanho do vetor armazenado.
DIMENSAO_PADRAO = 384


class MockEmbeddingProvider(EmbeddingProvider):
    """Gera vetor deterministico a partir do hash do texto, sem rede.

    Args:
        model: nome reportado nos metadados; util para distinguir execucoes.
        dimension: tamanho do vetor gerado; por padrao, o do modelo real.
    """

    name: ClassVar[str] = "mock"
    dimension: ClassVar[int] = DIMENSAO_PADRAO

    def __init__(self, *, model: str = "mock", dimension: int = DIMENSAO_PADRAO) -> None:
        self.model = model
        self.dimension = dimension

    async def embed(self, texts: list[str]) -> EmbeddingResult:
        inicio = time.perf_counter()
        vetores = tuple(_vetor_deterministico(texto, self.dimension) for texto in texts)
        return EmbeddingResult(
            vectors=vetores,
            provider=self.name,
            model=self.model,
            dimension=self.dimension,
            metadata={"mock": "true", "latency_ms": str((time.perf_counter() - inicio) * 1000)},
        )


def _vetor_deterministico(texto: str, dimensao: int) -> tuple[float, ...]:
    """Converte o texto num vetor normalizado, estavel entre execucoes.

    O hash alimenta um gerador simples, sem o pacote ``random`` (nao precisa
    de qualidade criptografica, so reprodutibilidade): cada byte do digest
    vira uma componente, repetindo o digest quando a dimensao excede os bytes
    disponiveis. O resultado e normalizado para manter a comparacao de
    similaridade de cosseno no mesmo intervalo que o provedor real produz.
    """

    digest = hashlib.sha256(texto.encode("utf-8")).digest()
    brutos = [digest[i % len(digest)] / 255.0 - 0.5 for i in range(dimensao)]
    norma = sum(valor * valor for valor in brutos) ** 0.5
    if norma == 0:
        return tuple(0.0 for _ in brutos)
    return tuple(valor / norma for valor in brutos)
