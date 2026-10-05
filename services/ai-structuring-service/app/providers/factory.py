"""Selecao do provedor de LLM a partir do ambiente (RNF03).

``LLM_PROVIDER`` decide qual implementacao atende as chamadas. Quem consome
pede ``get_llm_provider()`` e recebe algo que cumpre ``LLMProvider`` - trocar de
fornecedor e mudar a variavel, nunca o codigo de chamada.

Provedores registrados:
    ``mock``    resposta fixa, sem rede e sem chave; padrao em desenvolvimento
                e o unico usado na CI (RNF12).
    ``http``    API de chat completions compativel com OpenAI, com endpoint,
                modelo e chave vindos do ambiente (RNF11).

Nome desconhecido falha na criacao, com a lista do que existe - erro de
configuracao aparece na subida do servico, nao no meio de uma demanda.
"""

from collections.abc import Callable, Mapping
from typing import Final

from app.core.config import Settings, get_settings
from app.providers.base import LLMProvider
from app.providers.http_llm_provider import HttpLLMProvider
from app.providers.mock_provider import MockLLMProvider

#: Nome em ``LLM_PROVIDER`` -> fabrica do provedor correspondente.
PROVEDORES: Final[Mapping[str, Callable[[Settings], LLMProvider]]] = {
    MockLLMProvider.name: lambda settings: MockLLMProvider(model=settings.llm_model),
    HttpLLMProvider.name: HttpLLMProvider,
}


def get_llm_provider(settings: Settings | None = None) -> LLMProvider:
    """Cria o provedor indicado por ``LLM_PROVIDER``.

    Args:
        settings: configuracao a usar; por padrao, a do ambiente.

    Returns:
        Implementacao de ``LLMProvider`` pronta para uso.

    Raises:
        ValueError: ``LLM_PROVIDER`` nao corresponde a nenhum provedor
            registrado.
    """

    settings = settings or get_settings()
    nome = settings.llm_provider.casefold()
    fabrica = PROVEDORES.get(nome)
    if fabrica is None:
        disponiveis = ", ".join(sorted(PROVEDORES))
        raise ValueError(
            f"LLM_PROVIDER={settings.llm_provider!r} nao corresponde a nenhum provedor "
            f"registrado. Disponiveis: {disponiveis}."
        )
    return fabrica(settings)
