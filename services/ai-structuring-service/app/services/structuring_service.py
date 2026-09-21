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

Este modulo implementa hoje os passos 1 a 4 e o tratamento de falha que os
cerca (RF11, RNF05; **RF13.1** e **RF18.1** no Documento Consolidado de
Requisitos v1.0). ``structure`` faz a chamada crua ao provedor; ``structure_course``
encadeia prompt versionado, chamada e validacao de schema, e e o caso de uso
exposto em ``POST /api/v1/structuring``.

O passo 5 continua pendente: ``generate-syllabus.v1`` ainda e rascunho, entao a
ementa e os objetivos devolvidos hoje sao os que o proprio cliente descreveu no
texto, extraidos junto com os demais campos (RF12 parcial). Os passos 6 e 7
entram com os cards de RNF04 e RF13.

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

Diagnostico da resposta recusada (RNF05)
----------------------------------------

Resposta que nao passa no schema e recusada antes de virar resultado, e a
recusa e registrada em log - sem ela, o operador ve um 502 e ninguem consegue
dizer o que o modelo devolveu de errado.

O registro sai em dois niveis, porque o texto recusado e produto da demanda do
cliente e nao pode circular em log de rotina (RNF10):

``WARNING``
    sempre. Diz qual demanda falhou, qual prompt foi usado, quantas tentativas
    houve, **quais campos violaram o contrato** e o tamanho da resposta. Sao
    nomes de campo do contrato e numeros - nada do que o cliente escreveu, nada
    de credencial (RNF11).

``DEBUG``
    apenas quando ``LOG_LEVEL=DEBUG`` for ligado de proposito para investigar.
    Traz a resposta bruta truncada em ``RAW_RESPONSE_LOG_LIMIT`` caracteres.

O corpo de erro devolvido ao operador nao repete nada disso: leva o codigo, a
demanda e o resumo das violacoes por campo, montado pelo dominio sem o valor
recusado.

Este modulo usa ``logging`` da biblioteca padrao. O log estruturado em JSON,
com ``request_id`` correlacionado entre servicos, e de ``app.core.logging``,
que segue como stub e tem card proprio.

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
import logging
import time
from collections.abc import Awaitable, Callable
from dataclasses import dataclass, replace
from typing import Any, Final

from tenacity import AsyncRetrying, RetryCallState, retry_if_exception, stop_after_attempt

from app.core.config import Settings
from app.core.exceptions import LLMInvalidResponseError, LLMProviderError
from app.domain.course import (
    StructuredCourse,
    schema_do_curso_estruturado,
    validar_curso_estruturado,
)
from app.prompts import carregar_prompt
from app.providers.base import CompletionParams, CompletionResult, LLMProvider

#: Log deste modulo. A configuracao (formato, nivel, correlacao) e do processo,
#: nunca fixada aqui - ver ``app.core.logging``.
_logger = logging.getLogger(__name__)

#: Teto de caracteres da resposta recusada registrada em nivel ``DEBUG``. O
#: texto e produto da demanda do cliente: o bastante para diagnosticar a
#: malformacao, nao o email inteiro de volta no arquivo de log (RNF10).
RAW_RESPONSE_LOG_LIMIT: Final[int] = 500

#: Base do backoff exponencial entre retentativas, em segundos.
BACKOFF_BASE_SECONDS: Final[float] = 0.5

#: Teto do backoff, para que a espera nao cresca sem limite (RNF06).
BACKOFF_MAX_SECONDS: Final[float] = 8.0

#: Funcao de espera entre tentativas; injetavel para o teste nao dormir.
Sleep = Callable[[float], Awaitable[Any]]

#: Prompt versionado que extrai os campos pedagogicos do texto da demanda (RF11).
EXTRACTION_PROMPT_NAME: Final[str] = "extract-requirements"

#: Versao usada quando o chamador nao pede outra: a que esta marcada como
#: ``status: ativo`` no catalogo. Versao nova e arquivo novo, nunca edicao no
#: lugar - ver ``app/prompts/README.md``. Ao publicar uma versao nova, mova este
#: padrao junto: prompt ativo que ninguem carrega nao vale nada.
DEFAULT_PROMPT_VERSION: Final[str] = "v3"


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
        course: curso ja validado na forma canonica (RNF03); ``None`` quando a
            chamada nao passou por ``structure_course`` ou quando falhou.
        prompt_id: prompt versionado usado na execucao, ex.:
            ``extract-requirements.v1``. Acompanha a proveniencia do artefato
            (RNF04, RNF09).
    """

    demand: RawDemand
    attempts: int
    completion: CompletionResult | None = None
    error: LLMProviderError | None = None
    elapsed_ms: float = 0.0
    course: StructuredCourse | None = None
    prompt_id: str | None = None

    @property
    def succeeded(self) -> bool:
        """Indica se a execucao terminou com resultado utilizavel.

        Resultado bruto acompanhado de erro nao conta como sucesso: e o caso da
        resposta que chegou do provedor mas nao passou no schema do curso, que
        e falha e nao "quase certa" (ADR-0006).
        """

        return self.completion is not None and self.error is None

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

    def raise_for_course(self) -> StructuredCourse:
        """Devolve o curso validado ou levanta a falha tipada.

        E o que a rota chama antes de responder: ou ha curso na forma canonica,
        ou ha erro identificado - nunca um meio-termo (RF11, RNF03).

        Raises:
            LLMProviderError: a subclasse correspondente a causa da falha.
        """

        self.raise_for_error()
        if self.course is None:
            raise LLMInvalidResponseError("Estruturacao terminou sem curso validado.")
        return self.course

    def to_error_payload(self, request_id: str | None = None) -> dict[str, Any] | None:
        """Corpo de erro no formato da plataforma, ou ``None`` se houve sucesso."""

        if self.error is None:
            return None
        return self.error.to_error_payload(request_id)


class StructuringService:
    """Estrutura a demanda bruta: prompt, provedor e schema em um so fluxo.

    Dois niveis, de proposito:

    ``structure_course``
        o caso de uso de ponta a ponta (RF11). Monta o prompt versionado,
        chama o provedor e valida a resposta contra a forma canonica do curso
        antes de devolver qualquer coisa. E o que a rota
        ``POST /api/v1/structuring`` expoe.

    ``structure``
        a chamada crua ao provedor, com a politica de retentativa e o
        tratamento de falha (RNF05). Fica publica porque avaliacao de prompt e
        medicao de qualidade (RNF04) precisam do texto do modelo sem passar
        pela validacao.

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

    async def structure_course(
        self,
        demand: RawDemand,
        *,
        prompt_version: str = DEFAULT_PROMPT_VERSION,
    ) -> StructuringOutcome:
        """Estrutura a demanda de ponta a ponta e devolve o curso validado (RF11).

        Encadeia os quatro passos do caso de uso: monta o prompt versionado com
        o texto ja normalizado, chama o provedor com o schema de saida
        declarado (RNF03), valida a resposta contra ``StructuredCourse`` e so
        entao devolve o resultado.

        Nao levanta excecao, pela mesma razao que ``structure`` nao levanta: o
        chamador sempre recebe o desfecho com a demanda bruta em maos (RNF05).
        Resposta fora do schema vira ``LLMInvalidResponseError`` no desfecho -
        nao e aceita como "quase certa" (ADR-0006) - e a recusa e registrada em
        log para diagnostico, sem devolver o texto recusado a quem chamou. A
        fronteira HTTP chama ``raise_for_course`` e deixa o handler de
        ``app.main`` traduzir o erro.

        Args:
            demand: demanda bruta ja persistida pelo ingestion-service.
            prompt_version: versao do prompt de extracao a usar; por padrao, a
                ativa no catalogo.

        Returns:
            ``StructuringOutcome`` com ``course`` preenchido quando deu certo,
            ou com o erro tipado quando nao deu.

        Raises:
            ValueError: ``prompt_version`` nao existe no catalogo de prompts.
                E erro de configuracao do chamador, nao falha de execucao, e
                por isso sobe em vez de virar desfecho.
        """

        prompt = carregar_prompt(EXTRACTION_PROMPT_NAME, prompt_version)
        outcome = await self.structure(
            demand,
            prompt=prompt.render(texto_normalizado=demand.text),
            params=self._parametros_da_extracao(),
        )
        outcome = replace(outcome, prompt_id=prompt.identificador)
        if outcome.completion is None:
            return outcome

        try:
            curso = validar_curso_estruturado(outcome.completion.text)
        except LLMInvalidResponseError as erro:
            _registrar_resposta_recusada(
                demand=demand,
                prompt_id=prompt.identificador,
                attempts=outcome.attempts,
                erro=erro,
                bruto=outcome.completion.text,
            )
            erro.add_context(
                demand_id=demand.demand_id,
                attempts=outcome.attempts,
                prompt=prompt.identificador,
                retryable=erro.retryable,
            )
            return replace(outcome, error=erro)

        return replace(outcome, course=curso)

    def _parametros_da_extracao(self) -> CompletionParams:
        """Parametros da chamada de extracao, todos vindos do ambiente (RNF11).

        Temperatura baixa e schema declarado sao o que sustenta a saida de
        forma fixa entre execucoes (RNF03); o provedor repassa o schema ao
        fornecedor quando este aceitar saida estruturada, mas a validacao que
        vale e sempre a de ``validar_curso_estruturado``.
        """

        return CompletionParams(
            model=self._settings.llm_model,
            temperature=self._settings.llm_temperature,
            timeout_seconds=self._settings.llm_timeout_seconds,
            response_schema=schema_do_curso_estruturado(),
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


def _registrar_resposta_recusada(
    *,
    demand: RawDemand,
    prompt_id: str,
    attempts: int,
    erro: LLMInvalidResponseError,
    bruto: str,
) -> None:
    """Registra em log a resposta recusada pelo schema, para diagnostico (RNF05).

    Dois registros, com finalidades diferentes: o de ``WARNING`` da o suficiente
    para saber que houve recusa e onde o contrato quebrou, e pode ficar ligado
    sempre; o de ``DEBUG`` guarda a resposta bruta truncada e so aparece quando
    alguem liga ``LOG_LEVEL=DEBUG`` para investigar um caso especifico.

    Nenhum dos dois expoe credencial (RNF11), e o de rotina nao repete o que o
    cliente escreveu (RNF10).

    Args:
        demand: demanda em processamento, para correlacionar log e reprocessamento.
        prompt_id: prompt versionado usado na chamada, ex.: ``extract-requirements.v2``.
        attempts: tentativas gastas ate a resposta recusada.
        erro: falha tipada levantada pela validacao de schema.
        bruto: texto devolvido pelo provedor, exatamente como chegou.
    """

    campos = erro.violated_fields()
    _logger.warning(
        "Resposta do provedor recusada pelo schema do curso estruturado "
        "(demand_id=%s, prompt=%s, tentativas=%d, campos=%s, caracteres=%d).",
        demand.demand_id,
        prompt_id,
        attempts,
        ", ".join(campos) if campos else "nao identificados",
        len(bruto),
    )
    _logger.debug(
        "Resposta bruta recusada (demand_id=%s, truncada em %d caracteres): %s",
        demand.demand_id,
        RAW_RESPONSE_LOG_LIMIT,
        _truncar_para_log(bruto),
    )


def _truncar_para_log(bruto: str) -> str:
    """Corta o texto em ``RAW_RESPONSE_LOG_LIMIT`` caracteres e avisa o corte.

    O aviso importa no diagnostico: sem ele nao da para distinguir resposta que
    terminou torta de resposta que foi cortada aqui.
    """

    if len(bruto) <= RAW_RESPONSE_LOG_LIMIT:
        return bruto
    restante = len(bruto) - RAW_RESPONSE_LOG_LIMIT
    return f"{bruto[:RAW_RESPONSE_LOG_LIMIT]}... [+{restante} caracteres truncados]"


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
