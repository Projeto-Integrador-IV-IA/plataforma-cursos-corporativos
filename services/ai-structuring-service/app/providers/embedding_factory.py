"""Selecao do provedor de embedding a partir do ambiente (RF29, espelha ``factory.py``).

``EMBEDDING_PROVIDER`` decide qual implementacao gera os vetores. Quem
consome pede ``get_embedding_provider()`` e recebe algo que cumpre
``EmbeddingProvider`` - trocar de modelo e mudar a variavel, nunca o codigo
de chamada.

Provedores registrados:
    ``mock``        vetor deterministico por hash, sem rede; padrao em
                     desenvolvimento e o unico usado na CI (RNF12).
    ``fastembed``    modelo local em ONNX, baixado uma vez e depois offline.

Nome desconhecido falha na criacao, com a lista do que existe - erro de
configuracao aparece na subida do servico, nao no meio de uma demanda.
"""

from collections.abc import Callable, Mapping
from typing import Final

from app.core.config import Settings, get_settings
from app.providers.embedding_base import EmbeddingProvider
from app.providers.fastembed_provider import FastEmbedProvider
from app.providers.mock_embedding_provider import MockEmbeddingProvider

#: Nome em ``EMBEDDING_PROVIDER`` -> fabrica do provedor correspondente.
PROVEDORES_DE_EMBEDDING: Final[Mapping[str, Callable[[Settings], EmbeddingProvider]]] = {
    MockEmbeddingProvider.name: lambda settings: MockEmbeddingProvider(
        model=settings.embedding_model
    ),
    FastEmbedProvider.name: lambda settings: FastEmbedProvider(model=settings.embedding_model),
}


def get_embedding_provider(settings: Settings | None = None) -> EmbeddingProvider:
    """Cria o provedor de embedding indicado por ``EMBEDDING_PROVIDER``.

    Args:
        settings: configuracao a usar; por padrao, a do ambiente.

    Returns:
        Implementacao de ``EmbeddingProvider`` pronta para uso.

    Raises:
        ValueError: ``EMBEDDING_PROVIDER`` nao corresponde a nenhum provedor
            registrado.
    """

    settings = settings or get_settings()
    nome = settings.embedding_provider.casefold()
    fabrica = PROVEDORES_DE_EMBEDDING.get(nome)
    if fabrica is None:
        disponiveis = ", ".join(sorted(PROVEDORES_DE_EMBEDDING))
        raise ValueError(
            f"EMBEDDING_PROVIDER={settings.embedding_provider!r} nao corresponde a nenhum "
            f"provedor registrado. Disponiveis: {disponiveis}."
        )
    return fabrica(settings)
