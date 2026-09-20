"""Caso de uso: estruturacao do curso por IA (RF11, RF12, RF13).

Fluxo previsto de ponta a ponta:
    1. receber o texto normalizado e o identificador da demanda;
    2. montar o prompt versionado de extracao (RF11);
    3. chamar o provedor de LLM com schema de saida definido (RNF03);
    4. validar a resposta contra o JSON Schema - resposta invalida e falha,
       nao e aceita "quase certa";
    5. montar o prompt de ementa a partir dos requisitos extraidos (RF12);
    6. registrar metricas da execucao (RNF04) e custo estimado (RNF12);
    7. devolver o curso estruturado para anexacao a negociacao (RF13).

Este modulo implementa hoje o passo 3 e o tratamento de falha que o cerca
(RNF05; **RF18.1** no Documento Consolidado de Requisitos v1.0). Os passos 2,
4 e 5 dependem do prompt versionado e do schema fixo, e entram com os cards de
RF11, RF12 e RNF03.

Tratamento de falha (RNF05)
---------------------------

Tres garantias, nesta ordem:

**A entrada recebida nunca e descartada.** ``RawDemand`` e imutavel e
atravessa a execucao inteira: sucesso ou falha, o desfecho devolvido carrega a
mesma demanda que entrou, pronta para reprocessamento sem que o operador
precise recolar o texto. A persistencia do bruto e anterior e externa a este
servico - quem grava e o ingestion-service, antes de qualquer chamada ao LLM -,
entao falhar aqui nao tem como desfazer registro nenhum: este servico nao abre
transacao e nao escreve no banco de outro microsservico.

**O chamador sempre recebe resposta.** ``structure`` nao deixa excecao de
provedor escapar: devolve um ``StructuringOutcome`` que diz se houve sucesso,
quantas tentativas foram gastas, quanto tempo levou (RNF06) e, quando falhou,
qual foi o erro tipado. A fronteira HTTP chama ``raise_for_error`` e deixa o
handler registrado em ``app.main`` traduzir o erro no corpo unico da
plataforma (RNF02).

**O erro identifica a causa e o que fazer.** O codigo estavel distingue
timeout, indisponibilidade, limite de uso e resposta invalida; os detalhes
dizem qual demanda falhou, quantas tentativas houve e se repetir tem chance de
sucesso (``retryable``). Nada disso expoe credencial (RNF11) nem dado pessoal
do cliente (RNF10).

Politica de retentativa
-----------------------

Fica aqui, e apenas aqui: o provedor traduz o transporte em erro tipado, o
caso de uso decide se insiste. Assim qualquer provedor registrado - inclusive
um futuro, com dialeto proprio - herda a mesma politica sem reimplementa-la.

Implementada com ``tenacity``: no maximo ``LLM_MAX_RETRIES`` repeticoes alem da
primeira tentativa, somente para falhas marcadas como ``retryable``
(indisponibilidade, timeout, limite de uso). Resposta invalida nao e retentada
- repetir sem mudar prompt, parametros ou configuracao tende a repetir o erro.
O intervalo e exponencial, exceto quando o fornecedor informa ``Retry-After``,
que e respeitado como veio.
"""

import asyncio
import time
from collections.abc import Awaitable, Callable
from dataclasses import dataclass, replace
from typing import Any, Final

from tenacity import AsyncRetrying, RetryCallState, retry_if_exception, stop_after_attempt

from app.core.config import Settings
from app.core.exceptions import LLMInvalidResponseError, LLMProviderError
from app.providers.base import CompletionParams, CompletionResult, LLMProvider

#: Base do backoff exponencial entre retentativas, em segundos.
BACKOFF_BASE_SECONDS: Final[float] = 0.5

#: Teto do backoff, para que a espera nao cresca sem limite (RNF06).
BACKOFF_MAX_SECONDS: Final[float] = 8.0

#: Funcao de espera entre tentativas; injetavel para o teste nao dormir.
Sleep = Callable[[float], Awaitable[Any]]


@dataclass(frozen=True, slots=True)
class RawDemand:
    """Demanda bruta que entra na estruturacao.

    Imutavel de proposito: o caso de uso nao reescreve nem trunca o que o
    operador colou. E a copia em memoria do registro que o ingestion-service ja
    persistiu antes desta chamada (RNF05, RNF09).

    Attributes:
        demand_id: identificador da demanda na negociacao, usado para
            correlacionar log, metrica e reprocessamento.
        text: texto recebido, ja normalizado pelo ingestion-service (RF10).
    """

    demand_id: str
    text: str


@dataclass(frozen=True, slots=True)
class StructuringOutcome:
    """Desfecho de uma tentativa de estruturacao, com ou sem sucesso.

    Attributes:
        demand: a mesma demanda que entrou - e o que garante que a falha nao
            deixa o chamador sem o texto original (RNF05).
        attempts: tentativas gastas, contando a primeira.
        completion: saida bruta do modelo; ``None`` quando houve falha.
        error: falha tipada do provedor; ``None`` quando houve sucesso.
        elapsed_ms: tempo de parede da execucao inteira, incluindo as esperas
            entre tentativas (RNF06).
    """

    demand: RawDemand
    attempts: int
    completion: CompletionResult | None = None
    error: LLMProviderError | None = None
    elapsed_ms: float = 0.0

    @property
    def succeeded(self) -> bool:
        """Indica se o provedor devolveu resultado."""

        return self.completion is not None

    @property
    def retryable(self) -> bool:
        """Indica se reprocessar a demanda tem chance de sucesso."""

        return self.error is not None and self.error.retryable

    def raise_for_error(self) -> CompletionResult:
        """Devolve o resultado ou levanta a falha tipada.

        Usado na fronteira HTTP, onde o handler de ``app.main`` converte a
        excecao no corpo de erro da plataforma (RNF02).

        Raises:
            LLMProviderError: a subclasse correspondente a causa da falha.
        """

        if self.error is not None:
            raise self.error
        if self.completion is None:
            raise LLMInvalidResponseError("Estruturacao terminou sem resultado e sem falha.")
        return self.completion

    def to_error_payload(self, request_id: str | None = None) -> dict[str, Any] | None:
        """Corpo de erro no formato da plataforma, ou ``None`` se houve sucesso."""

        if self.error is None:
            return None
        return self.error.to_error_payload(request_id)


class StructuringService:
    """Executa a chamada ao provedor de LLM para uma demanda bruta (RNF05).

    Args:
        provider: implementacao de ``LLMProvider``, obtida de
            ``get_llm_provider()`` - o caso de uso nao conhece fornecedor.
        settings: configuracao do ambiente; fornece timeout, teto de
            retentativas e temperatura (RNF11).
        sleep: espera entre tentativas. Injetavel para que o teste exercite a
            politica de retentativa sem dormir de verdade.
    """

    def __init__(
        self,
        provider: LLMProvider,
        settings: Settings,
        *,
        sleep: Sleep | None = None,
    ) -> None:
        self._provider = provider
        self._settings = settings
        self._sleep = sleep or asyncio.sleep

    async def structure(
        self,
        demand: RawDemand,
        *,
        prompt: str | None = None,
        params: CompletionParams | None = None,
    ) -> StructuringOutcome:
        """Envia a demanda ao provedor e devolve o desfecho, com ou sem falha.

        Nao levanta excecao de provedor: falha vira ``StructuringOutcome`` com
        o erro tipado, de modo que o chamador receba sempre uma resposta e
        continue com a demanda bruta em maos (RNF05).

        Args:
            demand: demanda bruta ja persistida pelo ingestion-service.
            prompt: texto ja montado a partir do prompt versionado (RF11).
                Ausente, o texto da demanda segue como esta - a montagem do
                prompt entra com o card de RF11.
            params: parametros da chamada; o timeout do ambiente e aplicado
                quando o chamador nao informa um.

        Returns:
            ``StructuringOutcome`` com o resultado ou com a falha tipada.
        """

        enviado = demand.text if prompt is None else prompt
        parametros = self._com_padroes(params)
        inicio = time.perf_counter()
        tentativas = 0
        resultado: CompletionResult | None = None

        try:
            async for tentativa in self._politica_de_retentativa():
                with tentativa:
                    tentativas = tentativa.retry_state.attempt_number
                    resultado = await self._provider.complete(enviado, parametros)
        except LLMProviderError as erro:
            erro.add_context(
                demand_id=demand.demand_id,
                attempts=tentativas,
                retryable=erro.retryable,
            )
            return StructuringOutcome(
                demand=demand,
                attempts=tentativas,
                error=erro,
                elapsed_ms=_decorrido_ms(inicio),
            )

        return StructuringOutcome(
            demand=demand,
            attempts=tentativas,
            completion=resultado,
            elapsed_ms=_decorrido_ms(inicio),
        )

    def _politica_de_retentativa(self) -> AsyncRetrying:
        """Monta a politica de retentativa a partir do ambiente."""

        return AsyncRetrying(
            stop=stop_after_attempt(self._settings.llm_max_retries + 1),
            retry=retry_if_exception(_e_retentavel),
            wait=_espera,
            sleep=self._sleep,
            reraise=True,
        )

    def _com_padroes(self, params: CompletionParams | None) -> CompletionParams:
        """Completa os parametros com o timeout do ambiente (RNF06, RNF11)."""

        parametros = params or CompletionParams()
        if parametros.timeout_seconds is not None:
            return parametros
        return replace(parametros, timeout_seconds=self._settings.llm_timeout_seconds)


def _e_retentavel(erro: BaseException) -> bool:
    """Decide se vale repetir a chamada depois desta falha.

    Somente falha tipada do provedor marcada como ``retryable``. Qualquer outra
    excecao e defeito de programacao e sobe imediatamente, sem retentativa.
    """

    return isinstance(erro, LLMProviderError) and erro.retryable


def _espera(retry_state: RetryCallState) -> float:
    """Backoff exponencial com teto, respeitando ``Retry-After`` quando houver."""

    falha = retry_state.outcome.exception() if retry_state.outcome is not None else None
    sugerido = getattr(falha, "retry_after_seconds", None)
    if sugerido is not None:
        return float(sugerido)
    return min(BACKOFF_BASE_SECONDS * (2 ** (retry_state.attempt_number - 1)), BACKOFF_MAX_SECONDS)


def _decorrido_ms(inicio: float) -> float:
    """Tempo de parede desde ``inicio``, em milissegundos (RNF06)."""

    return (time.perf_counter() - inicio) * 1000
