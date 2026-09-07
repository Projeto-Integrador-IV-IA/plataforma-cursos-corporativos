"""Provedores de LLM.

Unico pacote autorizado a importar SDK ou cliente HTTP de fornecedor. O
restante do servico importa somente a abstracao exposta aqui (RNF03, RNF13).
"""

from app.providers.base import (
    CompletionParams,
    CompletionResult,
    CompletionUsage,
    LLMProvider,
)

__all__ = [
    "CompletionParams",
    "CompletionResult",
    "CompletionUsage",
    "LLMProvider",
]
