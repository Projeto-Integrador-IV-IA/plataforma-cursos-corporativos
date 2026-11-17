"""Provedor de embedding local via ``fastembed`` (RF29).

``fastembed`` roda o modelo em ONNX, sem PyTorch e sem GPU - cabe no ambiente
de desenvolvimento e no MVP sem exigir infraestrutura paga nem chave de API.
O modelo (``sentence-transformers/all-MiniLM-L6-v2``, 384 dimensoes - a mesma
``EMBEDDING_DIMENSION`` que ``pipeline-service`` usa em ``segment_embeddings``)
e baixado do Hugging Face Hub na primeira chamada e fica em cache local; depois
disso a geracao e totalmente offline.

Selecionado por ``EMBEDDING_PROVIDER=fastembed``. O modelo roda em processo:
``TextEmbedding.embed`` e sincrono e consome CPU, entao a chamada vai para uma
thread (``asyncio.to_thread``) para nao bloquear o loop de eventos enquanto
atende outras requisicoes (mesma preocupacao de RNF06 que motiva timeout no
provedor de LLM).
"""

import asyncio
import time
from typing import ClassVar

from app.providers.embedding_base import EmbeddingProvider, EmbeddingResult

#: Modelo padrao: pequeno (~90 MB), rapido na CPU e com qualidade adequada para
#: recuperacao de trechos curtos em portugues e ingles.
MODELO_PADRAO = "sentence-transformers/all-MiniLM-L6-v2"

#: Dimensao do vetor que este modelo produz - fixa por modelo, nao configuravel.
DIMENSAO_PADRAO = 384


class FastEmbedProvider(EmbeddingProvider):
    """Gera embeddings localmente, via ONNX, sem rede apos o primeiro uso.

    Args:
        model: identificador do modelo no catalogo do ``fastembed``/Hugging
            Face Hub; por padrao, ``MODELO_PADRAO``.
    """

    name: ClassVar[str] = "fastembed"
    dimension: ClassVar[int] = DIMENSAO_PADRAO

    def __init__(self, *, model: str = MODELO_PADRAO) -> None:
        self.model = model
        self._modelo = None

    def _carregar_modelo(self):
        if self._modelo is None:
            from fastembed import TextEmbedding

            self._modelo = TextEmbedding(model_name=self.model)
        return self._modelo

    async def embed(self, texts: list[str]) -> EmbeddingResult:
        inicio = time.perf_counter()
        vetores_lista = await asyncio.to_thread(self._gerar, texts)
        vetores = tuple(tuple(float(valor) for valor in vetor) for vetor in vetores_lista)
        dimensao = len(vetores[0]) if vetores else self.dimension
        return EmbeddingResult(
            vectors=vetores,
            provider=self.name,
            model=self.model,
            dimension=dimensao,
            metadata={"latency_ms": str((time.perf_counter() - inicio) * 1000)},
        )

    def _gerar(self, texts: list[str]) -> list[object]:
        modelo = self._carregar_modelo()
        return list(modelo.embed(texts))
