"""Excecoes de dominio e traducao para respostas HTTP.

Erros previsiveis viram excecoes tipadas aqui e sao traduzidos em um corpo de
erro unico para toda a plataforma, de modo que o frontend trate qualquer
servico da mesma forma (RNF02).

Formato de erro acordado entre os servicos
(``packages/contracts/schemas/error.schema.json``):
    {"error": {"code": "LLM_TIMEOUT", "message": "...", "details": {...}}}

Hierarquia implementada:
    PlatformError                   base de todas
    └── UpstreamError               falha de servico dependente     -> 502
        └── LLMProviderError        falha do provedor de LLM (RNF05)
            ├── LLMUnavailableError    fornecedor fora do ar        -> 503
            ├── LLMTimeoutError        estourou o tempo maximo      -> 504
            ├── LLMRateLimitError      limite de uso/cota atingido  -> 429
            └── LLMInvalidResponseError resposta ilegivel           -> 502

As quatro condicoes de falha do provedor sao as unicas formas de ``complete``
terminar sem resultado (ver ``app.providers.base``). Excecao de SDK ou de
biblioteca HTTP e traduzida para uma delas **dentro** de ``app.providers`` -
nao vaza para o resto do servico.

As demais ramificacoes previstas para a plataforma (recurso inexistente,
entrada invalida, conflito de etapa, autenticacao e permissao) chegam com os
cards dos requisitos que as exigem - nao ha uso para elas neste servico hoje.
Os handlers do FastAPI sao registrados em ``app.main`` quando a aplicacao
existir.
"""

from collections.abc import Mapping
from typing import Any, ClassVar


class PlatformError(Exception):
    """Base de todo erro previsivel do servico.

    Carrega o codigo estavel, a mensagem exibivel ao operador e um contexto
    opcional, na mesma forma do contrato de erro da plataforma (RNF02).

    Attributes:
        code: codigo legivel por maquina, estavel entre versoes.
        http_status: status HTTP correspondente, usado pelo handler.
        default_message: mensagem usada quando o chamador nao informa uma.
    """

    code: ClassVar[str] = "INTERNAL_ERROR"
    http_status: ClassVar[int] = 500
    default_message: ClassVar[str] = "Erro interno do servico."

    def __init__(
        self,
        message: str | None = None,
        *,
        details: Mapping[str, Any] | None = None,
    ) -> None:
        self.message = message or self.default_message
        self.details: dict[str, Any] = dict(details or {})
        super().__init__(self.message)

    def to_error_payload(self, request_id: str | None = None) -> dict[str, Any]:
        """Monta o corpo de erro no formato unico da plataforma (RNF02).

        A mensagem nao expoe detalhe interno de infraestrutura (RNF10) e o
        contexto nunca deve conter credencial (RNF11).
        """

        error: dict[str, Any] = {"code": self.code, "message": self.message}
        if self.details:
            error["details"] = dict(self.details)
        if request_id:
            error["request_id"] = request_id
        return {"error": error}


class UpstreamError(PlatformError):
    """Falha de um servico do qual este depende."""

    code: ClassVar[str] = "UPSTREAM_ERROR"
    http_status: ClassVar[int] = 502
    default_message: ClassVar[str] = "Servico dependente respondeu com falha."


class LLMProviderError(UpstreamError):
    """Base das falhas do provedor de LLM (RNF05).

    A demanda bruta ja esta persistida pelo ``ingestion-service`` antes da
    chamada, entao nenhuma destas falhas perde dado: a operacao pode ser
    repetida.

    Attributes:
        retryable: indica se repetir a chamada tem chance de sucesso. Orienta a
            politica de retentativa do provedor concreto (``LLM_MAX_RETRIES``).
    """

    code: ClassVar[str] = "LLM_ERROR"
    http_status: ClassVar[int] = 502
    default_message: ClassVar[str] = "Falha na chamada ao provedor de LLM."
    retryable: ClassVar[bool] = False

    def __init__(
        self,
        message: str | None = None,
        *,
        provider: str | None = None,
        model: str | None = None,
        details: Mapping[str, Any] | None = None,
    ) -> None:
        super().__init__(message, details=details)
        self.provider = provider
        self.model = model
        if provider is not None:
            self.details.setdefault("provider", provider)
        if model is not None:
            self.details.setdefault("model", model)


class LLMUnavailableError(LLMProviderError):
    """Fornecedor indisponivel: fora do ar, recusando conexao ou erro 5xx."""

    code: ClassVar[str] = "LLM_UNAVAILABLE"
    http_status: ClassVar[int] = 503
    default_message: ClassVar[str] = "Provedor de LLM indisponivel no momento."
    retryable: ClassVar[bool] = True


class LLMTimeoutError(LLMProviderError):
    """Fornecedor nao respondeu dentro de ``LLM_TIMEOUT_SECONDS`` (RNF06)."""

    code: ClassVar[str] = "LLM_TIMEOUT"
    http_status: ClassVar[int] = 504
    default_message: ClassVar[str] = "Provedor de LLM excedeu o tempo maximo de resposta."
    retryable: ClassVar[bool] = True

    def __init__(
        self,
        message: str | None = None,
        *,
        timeout_seconds: float | None = None,
        provider: str | None = None,
        model: str | None = None,
        details: Mapping[str, Any] | None = None,
    ) -> None:
        super().__init__(message, provider=provider, model=model, details=details)
        self.timeout_seconds = timeout_seconds
        if timeout_seconds is not None:
            self.details.setdefault("timeout_seconds", timeout_seconds)


class LLMRateLimitError(LLMProviderError):
    """Limite de requisicoes ou de cota atingido - relevante na camada gratuita (RNF12)."""

    code: ClassVar[str] = "LLM_RATE_LIMITED"
    http_status: ClassVar[int] = 429
    default_message: ClassVar[str] = "Limite de uso do provedor de LLM atingido."
    retryable: ClassVar[bool] = True

    def __init__(
        self,
        message: str | None = None,
        *,
        retry_after_seconds: float | None = None,
        provider: str | None = None,
        model: str | None = None,
        details: Mapping[str, Any] | None = None,
    ) -> None:
        super().__init__(message, provider=provider, model=model, details=details)
        self.retry_after_seconds = retry_after_seconds
        if retry_after_seconds is not None:
            self.details.setdefault("retry_after_seconds", retry_after_seconds)


class LLMInvalidResponseError(LLMProviderError):
    """Resposta do fornecedor ilegivel ou fora do formato esperado.

    Cobre corpo que nao e o esperado pela API do fornecedor e resposta que nao
    passa no JSON Schema da saida: resposta invalida e falha, nao e aceita como
    "quase certa" (ADR-0006). Repetir sem mudar prompt ou parametros tende a
    repetir o erro, por isso nao e retentavel por padrao.
    """

    code: ClassVar[str] = "LLM_INVALID_RESPONSE"
    http_status: ClassVar[int] = 502
    default_message: ClassVar[str] = "Resposta do provedor de LLM fora do formato esperado."
    retryable: ClassVar[bool] = False
