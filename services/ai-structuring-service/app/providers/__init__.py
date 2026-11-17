"""Provedores de LLM.

Unico pacote autorizado a importar SDK ou cliente HTTP de fornecedor. O
restante do servico importa somente a abstracao exposta aqui e pede a
implementacao concreta a ``get_llm_provider()``, que le ``LLM_PROVIDER``
do ambiente (RNF03, RNF13).
"""

from app.providers.base import (
    CompletionParams,
    CompletionResult,
    CompletionUsage,
    LLMProvider,
)
from app.providers.embedding_base import EmbeddingProvider, EmbeddingResult
from app.providers.embedding_factory import PROVEDORES_DE_EMBEDDING, get_embedding_provider
from app.providers.factory import PROVEDORES, get_llm_provider
from app.providers.fastembed_provider import FastEmbedProvider
from app.providers.http_llm_provider import HttpLLMProvider, OpenRouterProvider
from app.providers.mock_embedding_provider import MockEmbeddingProvider
from app.providers.mock_provider import MockLLMProvider

__all__ = [
    "PROVEDORES",
    "PROVEDORES_DE_EMBEDDING",
    "CompletionParams",
    "CompletionResult",
    "CompletionUsage",
    "EmbeddingProvider",
    "EmbeddingResult",
    "FastEmbedProvider",
    "HttpLLMProvider",
    "LLMProvider",
    "MockEmbeddingProvider",
    "MockLLMProvider",
    "OpenRouterProvider",
    "get_embedding_provider",
    "get_llm_provider",
]
