"""Contrato do provedor de embedding (RF29, espelhando ``providers/base.py`` de RNF03).

Mesma razao do contrato de LLM: nenhum modulo fora de ``app.providers`` pode
depender do SDK de um provedor de embedding especifico. Trocar de modelo (ou
de fornecedor, caso um dia exista um remoto) e configuracao, nunca
refatoracao.

``EmbeddingResult``
    Vetores devolvidos, na mesma ordem dos textos enviados, mais os metadados
    de execucao (provedor, modelo, dimensao). O modelo usado acompanha cada
    lote para registro de proveniencia (RNF08) - card #160 pede exatamente
    isso: "Modelo de embedding registrado por execucao".

``EmbeddingProvider``
    Classe abstrata que todo provedor implementa. Um unico metodo
    assincrono, ``embed``, que recebe os textos em lote (gerar um por vez
    seria uma chamada por trecho) e devolve o resultado ou levanta
    ``LLMProviderError`` - os mesmos tipos de falha do provedor de LLM
    (indisponibilidade, timeout) fazem sentido aqui tambem, entao nao ha
    hierarquia de excecao nova.
"""

from abc import ABC, abstractmethod
from collections.abc import Sequence
from dataclasses import dataclass, field
from typing import ClassVar


@dataclass(frozen=True, slots=True)
class EmbeddingResult:
    """Vetores de uma chamada de embedding, com a proveniencia da execucao.

    Attributes:
        vectors: um vetor por texto de entrada, na mesma ordem.
        provider: provedor que atendeu a chamada (``EMBEDDING_PROVIDER``).
        model: identificador do modelo que gerou os vetores - vai para
            ``SegmentEmbeddingCreate.model`` no pipeline-service, a chave que
            distingue uma gravacao de outra para o mesmo trecho (RNF09).
        dimension: tamanho de cada vetor. Constante por modelo; existe aqui
            para o chamador validar sem reabrir o vetor.
    """

    vectors: tuple[tuple[float, ...], ...]
    provider: str
    model: str
    dimension: int
    metadata: dict[str, str] = field(default_factory=dict)


class EmbeddingProvider(ABC):
    """Interface que todo provedor de embedding precisa cumprir.

    Implementacoes vivem em ``app.providers``, ao lado de ``LLMProvider`` -
    mesma garantia de isolamento (``tests/unit/test_provider_isolation.py``).

    Attributes:
        name: identificador estavel do provedor, o mesmo valor aceito em
            ``EMBEDDING_PROVIDER`` (ex.: ``"mock"``, ``"fastembed"``).
        dimension: tamanho do vetor que este provedor produz.
    """

    name: ClassVar[str]
    dimension: ClassVar[int]

    @abstractmethod
    async def embed(self, texts: Sequence[str]) -> EmbeddingResult:
        """Gera um vetor por texto de entrada, na mesma ordem.

        Args:
            texts: trechos a converter em vetor. Lista vazia e erro de
                chamador, nao caso a tratar aqui - quem orquestra decide se
                vale a pena chamar com lote vazio.

        Returns:
            ``EmbeddingResult`` com um vetor por texto, na mesma ordem.

        Raises:
            LLMUnavailableError: provedor indisponivel ou erro de transporte.
            LLMTimeoutError: o provedor nao respondeu no tempo maximo.
        """
