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
from app.providers.factory import PROVEDORES, get_llm_provider
from app.providers.http_llm_provider import HttpLLMProvider
from app.providers.mock_provider import MockLLMProvider

__all__ = [
    "PROVEDORES",
    "CompletionParams",
    "CompletionResult",
    "CompletionUsage",
    "HttpLLMProvider",
    "LLMProvider",
    "MockLLMProvider",
    "get_llm_provider",
]
