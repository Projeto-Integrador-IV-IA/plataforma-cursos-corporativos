"""Contrato do provedor de LLM (RNF03, ADR-0006).

Abstrai qual API de linguagem esta em uso. O restante do servico depende desta
interface, nunca de um SDK especifico - trocar de provedor (OpenAI, Anthropic,
Gemini, mock) e questao de configuracao, nao de refatoracao (RNF13).

O contrato tem tres partes:

``CompletionParams``
    Parametros da chamada: modelo, temperatura, teto de tokens, timeout,
    instrucao de sistema e o schema de saida esperado (ADR-0006). Nenhum e
    obrigatorio - ausente significa "use o padrao do provedor", vindo da
    configuracao de ambiente (``LLM_MODEL``, ``LLM_TEMPERATURE``, ...).

``CompletionResult``
    Texto bruto devolvido pelo modelo mais os metadados de execucao (provedor,
    modelo, tokens, latencia). O texto sai daqui **sem validacao de schema**: a
    validacao contra o JSON Schema e responsabilidade do caso de uso, que trata
    resposta invalida como falha (ADR-0006). Os metadados sao insumo das
    metricas de qualidade (RNF04), do custo de operacao (RNF12) e da
    proveniencia gravada com o artefato (RNF09).

``LLMProvider``
    Classe abstrata que todo provedor implementa. Um unico metodo assincrono,
    ``complete``, que so pode terminar de duas formas: devolvendo um
    ``CompletionResult`` ou levantando um ``LLMProviderError``
    (``app.core.exceptions``). Nenhuma excecao de biblioteca HTTP ou de SDK
    pode vazar para fora de ``app.providers`` - e o que permite ao chamador
    tratar falha e timeout de forma uniforme, sem conhecer o fornecedor (RNF05).
"""

from abc import ABC, abstractmethod
from collections.abc import Mapping
from dataclasses import dataclass, field
from typing import Any, ClassVar


@dataclass(frozen=True, slots=True)
class CompletionParams:
    """Parametros de uma chamada de completacao.

    Todos opcionais: campo ausente significa usar o padrao do provedor, que por
    sua vez vem do ambiente (RNF11) - nunca fixado no codigo.

    Attributes:
        model: identificador do modelo alvo (``LLM_MODEL``).
        temperature: aleatoriedade da geracao; baixa para saida previsivel (RNF03).
        max_output_tokens: teto de tokens gerados, limite de custo (RNF12).
        timeout_seconds: tempo maximo da chamada, alinhado ao alvo de 15 s (RNF06).
        system_prompt: instrucao de sistema (papel e restricoes do modelo).
        response_schema: JSON Schema da saida esperada (ADR-0006). O provedor
            repassa ao fornecedor quando este suportar saida estruturada; a
            validacao definitiva acontece fora daqui.
    """

    model: str | None = None
    temperature: float | None = None
    max_output_tokens: int | None = None
    timeout_seconds: float | None = None
    system_prompt: str | None = None
    response_schema: Mapping[str, Any] | None = None


@dataclass(frozen=True, slots=True)
class CompletionUsage:
    """Consumo de tokens de uma chamada, contabilizado por RNF12."""

    prompt_tokens: int = 0
    completion_tokens: int = 0

    @property
    def total_tokens(self) -> int:
        """Soma dos tokens de entrada e de saida."""

        return self.prompt_tokens + self.completion_tokens


@dataclass(frozen=True, slots=True)
class CompletionResult:
    """Saida bruta do modelo com os metadados de execucao.

    Attributes:
        text: texto devolvido pelo modelo, ainda nao validado contra o schema.
        provider: provedor que atendeu a chamada (``LLM_PROVIDER``).
        model: modelo que efetivamente respondeu - pode diferir do solicitado,
            e e ele que vai para a proveniencia do artefato (RNF09).
        usage: tokens consumidos (RNF12).
        latency_ms: tempo de parede da chamada, em milissegundos (RNF04, RNF06).
        finish_reason: motivo de termino informado pelo fornecedor, quando houver.
        metadata: campos extras do fornecedor, sem contrato garantido. Nunca
            deve conter credencial (RNF11) nem dado pessoal do cliente (RNF10).
    """

    text: str
    provider: str
    model: str
    usage: CompletionUsage = field(default_factory=CompletionUsage)
    latency_ms: float = 0.0
    finish_reason: str | None = None
    metadata: Mapping[str, Any] = field(default_factory=dict)


class LLMProvider(ABC):
    """Interface que todo provedor de LLM precisa cumprir.

    Implementacoes vivem em ``app.providers``. Quem consome fala apenas com
    esta abstracao: nenhum modulo fora do pacote importa SDK de fornecedor.

    Attributes:
        name: identificador estavel do provedor, o mesmo valor aceito em
            ``LLM_PROVIDER`` (ex.: ``"mock"``). E ele que aparece em
            ``CompletionResult.provider`` e nos logs de proveniencia.
    """

    name: ClassVar[str]

    @abstractmethod
    async def complete(
        self,
        prompt: str,
        params: CompletionParams | None = None,
    ) -> CompletionResult:
        """Envia o prompt ao modelo e devolve o texto bruto com os metadados.

        Args:
            prompt: texto ja montado a partir do prompt versionado (RNF03).
            params: parametros da chamada; ``None`` usa os padroes do provedor.

        Returns:
            ``CompletionResult`` com o texto e os metadados de execucao.

        Raises:
            LLMTimeoutError: o fornecedor nao respondeu no tempo maximo.
            LLMRateLimitError: limite de uso ou de cota atingido.
            LLMUnavailableError: fornecedor indisponivel ou erro de transporte.
            LLMInvalidResponseError: resposta ilegivel ou fora do formato
                esperado do fornecedor.
        """
