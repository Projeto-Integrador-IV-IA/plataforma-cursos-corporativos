"""Provedor de LLM sobre API HTTP.

Implementacao concreta da interface definida em ``base.py``. O fornecedor
especifico e a familia de modelo sao decididos na avaliacao comparativa da
Fase 2 e chegam por configuracao (``LLM_PROVIDER``, ``LLM_MODEL``,
``LLM_BASE_URL``) - nunca fixados no codigo, para que trocar de fornecedor nao
exija reescrever o servico (RNF13).

Chave lida de ``LLM_API_KEY`` (RNF11) - nunca embutida no codigo, nunca
registrada em log nem devolvida em mensagem de erro.

**Formato da requisicao.** Fala o dialeto *chat completions* compativel com
OpenAI, hoje suportado por OpenAI, Groq, Ollama, OpenRouter e pelos endpoints
de compatibilidade de Anthropic e Gemini. Endpoint e caminho vem do ambiente
(``LLM_BASE_URL`` + ``LLM_COMPLETIONS_PATH``); fornecedor com dialeto proprio
ganha sua propria implementacao desta mesma interface, sem tocar no resto do
servico.

Pontos de atencao:
    - timeout configuravel por ``LLM_TIMEOUT_SECONDS``, alinhado ao alvo de
      15 s de RNF06;
    - retentativa com backoff limitada por ``LLM_MAX_RETRIES``, apenas para
      falhas marcadas como ``retryable`` - erro de requisicao ou resposta
      invalida nao e retentado;
    - temperatura baixa e schema de saida repassado ao fornecedor, para
      garantir formato previsivel (RNF03) - a validacao definitiva contra o
      JSON Schema fica com o caso de uso (ADR-0006);
    - contabilizacao de tokens por chamada, insumo do levantamento de custo
      de operacao (RNF12).

Traducao dos erros do transporte para as excecoes tipadas (RNF05):

    ==============================  ===========================
    Condicao                        Excecao
    ==============================  ===========================
    timeout de conexao ou leitura   ``LLMTimeoutError``
    HTTP 408 / 504                  ``LLMTimeoutError``
    HTTP 429                        ``LLMRateLimitError``
    HTTP 5xx                        ``LLMUnavailableError``
    erro de rede / conexao          ``LLMUnavailableError``
    demais HTTP 4xx                 ``LLMInvalidResponseError``
    corpo ilegivel ou incompleto    ``LLMInvalidResponseError``
    ==============================  ===========================

Nenhuma excecao de ``httpx`` atravessa esta fronteira.
"""

import asyncio
import time
from typing import Any, ClassVar, Final

import httpx

from app.core.config import Settings
from app.core.exceptions import (
    LLMInvalidResponseError,
    LLMProviderError,
    LLMRateLimitError,
    LLMTimeoutError,
    LLMUnavailableError,
)
from app.providers.base import (
    CompletionParams,
    CompletionResult,
    CompletionUsage,
    LLMProvider,
)

#: Base do backoff exponencial entre retentativas, em segundos.
BACKOFF_BASE_SECONDS: Final[float] = 0.5


class HttpLLMProvider(LLMProvider):
    """Provedor que conversa com uma API de chat completions por HTTP.

    Args:
        settings: configuracao lida do ambiente; fornece endpoint, modelo,
            chave, timeout, teto de retentativas e temperatura.
        client: cliente HTTP a reutilizar. Injetado nos testes para dispensar
            rede; em producao o provedor cria e mantem o seu.
    """

    name: ClassVar[str] = "http"

    def __init__(self, settings: Settings, client: httpx.AsyncClient | None = None) -> None:
        if settings.llm_base_url is None:
            raise ValueError("LLM_BASE_URL e obrigatoria para o provedor HTTP")
        self._settings = settings
        self._client = client
        self._client_proprio = client is None

    async def complete(
        self,
        prompt: str,
        params: CompletionParams | None = None,
    ) -> CompletionResult:
        """Envia o prompt ao fornecedor e devolve o texto bruto com metadados."""

        params = params or CompletionParams()
        payload = self._montar_payload(prompt, params)
        timeout = params.timeout_seconds or self._settings.llm_timeout_seconds
        inicio = time.perf_counter()

        resposta = await self._chamar_com_retentativa(payload, timeout)
        latency_ms = (time.perf_counter() - inicio) * 1000

        return self._traduzir_resposta(resposta, payload["model"], latency_ms)

    async def aclose(self) -> None:
        """Fecha o cliente HTTP, se este provedor for o dono dele."""

        if self._client is not None and self._client_proprio:
            await self._client.aclose()
            self._client = None

    # ------------------------------------------------------------------
    # Montagem da requisicao
    # ------------------------------------------------------------------

    def _montar_payload(self, prompt: str, params: CompletionParams) -> dict[str, Any]:
        mensagens: list[dict[str, str]] = []
        if params.system_prompt:
            mensagens.append({"role": "system", "content": params.system_prompt})
        mensagens.append({"role": "user", "content": prompt})

        payload: dict[str, Any] = {
            "model": params.model or self._settings.llm_model,
            "messages": mensagens,
            "temperature": (
                params.temperature
                if params.temperature is not None
                else self._settings.llm_temperature
            ),
        }
        if params.max_output_tokens is not None:
            payload["max_tokens"] = params.max_output_tokens
        if params.response_schema is not None:
            payload["response_format"] = {
                "type": "json_schema",
                "json_schema": {
                    "name": "structured_course",
                    "schema": dict(params.response_schema),
                },
            }
        return payload

    def _headers(self) -> dict[str, str]:
        headers = {"content-type": "application/json"}
        if self._settings.llm_api_key is not None:
            headers["authorization"] = f"Bearer {self._settings.llm_api_key.get_secret_value()}"
        return headers

    def _obter_client(self, timeout: float) -> httpx.AsyncClient:
        if self._client is None:
            self._client = httpx.AsyncClient(
                base_url=self._settings.llm_base_url or "",
                timeout=timeout,
            )
            self._client_proprio = True
        return self._client

    # ------------------------------------------------------------------
    # Chamada e traducao de falha
    # ------------------------------------------------------------------

    async def _chamar_com_retentativa(
        self,
        payload: dict[str, Any],
        timeout: float,
    ) -> httpx.Response:
        client = self._obter_client(timeout)
        url = self._url_completions()
        ultima_falha: LLMProviderError | None = None

        for tentativa in range(self._settings.llm_max_retries + 1):
            try:
                resposta = await client.post(
                    url,
                    json=payload,
                    headers=self._headers(),
                    timeout=timeout,
                )
            except httpx.TimeoutException as erro:
                ultima_falha = self._erro_de_timeout(timeout, payload["model"], erro)
            except httpx.HTTPError as erro:
                ultima_falha = LLMUnavailableError(
                    provider=self.name,
                    model=payload["model"],
                    details={"causa": type(erro).__name__},
                )
            else:
                if resposta.is_success:
                    return resposta
                ultima_falha = self._erro_de_status(resposta, payload["model"])

            if not ultima_falha.retryable or tentativa == self._settings.llm_max_retries:
                raise ultima_falha
            await asyncio.sleep(self._espera(tentativa, ultima_falha))

        raise ultima_falha  # pragma: no cover - o laco sempre sai antes

    def _url_completions(self) -> str:
        base = (self._settings.llm_base_url or "").rstrip("/")
        caminho = self._settings.llm_completions_path
        return f"{base}/{caminho.lstrip('/')}"

    def _erro_de_timeout(
        self,
        timeout: float,
        model: str,
        erro: httpx.TimeoutException,
    ) -> LLMTimeoutError:
        return LLMTimeoutError(
            timeout_seconds=timeout,
            provider=self.name,
            model=model,
            details={"causa": type(erro).__name__},
        )

    def _erro_de_status(self, resposta: httpx.Response, model: str) -> LLMProviderError:
        status = resposta.status_code
        details = {"status_code": status}

        if status in (408, 504):
            return LLMTimeoutError(
                timeout_seconds=self._settings.llm_timeout_seconds,
                provider=self.name,
                model=model,
                details=details,
            )
        if status == 429:
            return LLMRateLimitError(
                retry_after_seconds=_retry_after(resposta),
                provider=self.name,
                model=model,
                details=details,
            )
        if status >= 500:
            return LLMUnavailableError(provider=self.name, model=model, details=details)
        return LLMInvalidResponseError(
            f"Provedor de LLM recusou a requisicao (HTTP {status}).",
            provider=self.name,
            model=model,
            details=details,
        )

    def _espera(self, tentativa: int, falha: LLMProviderError) -> float:
        """Backoff exponencial, respeitando o ``Retry-After`` quando houver."""

        sugerido = getattr(falha, "retry_after_seconds", None)
        if sugerido is not None:
            return float(sugerido)
        return BACKOFF_BASE_SECONDS * (2**tentativa)

    # ------------------------------------------------------------------
    # Traducao da resposta
    # ------------------------------------------------------------------

    def _traduzir_resposta(
        self,
        resposta: httpx.Response,
        model_solicitado: str,
        latency_ms: float,
    ) -> CompletionResult:
        try:
            corpo = resposta.json()
            escolha = corpo["choices"][0]
            texto = escolha["message"]["content"]
        except (ValueError, KeyError, IndexError, TypeError) as erro:
            raise LLMInvalidResponseError(
                provider=self.name,
                model=model_solicitado,
                details={"causa": type(erro).__name__},
            ) from erro

        if not isinstance(texto, str) or not texto.strip():
            raise LLMInvalidResponseError(
                "Provedor de LLM devolveu conteudo vazio.",
                provider=self.name,
                model=model_solicitado,
            )

        uso = corpo.get("usage") or {}
        return CompletionResult(
            text=texto,
            provider=self.name,
            model=corpo.get("model") or model_solicitado,
            usage=CompletionUsage(
                prompt_tokens=_inteiro(uso.get("prompt_tokens")),
                completion_tokens=_inteiro(uso.get("completion_tokens")),
            ),
            latency_ms=latency_ms,
            finish_reason=escolha.get("finish_reason"),
        )


def _retry_after(resposta: httpx.Response) -> float | None:
    """Le o cabecalho ``Retry-After`` em segundos, quando presente e numerico."""

    bruto = resposta.headers.get("retry-after")
    try:
        return float(bruto) if bruto is not None else None
    except ValueError:
        return None


def _inteiro(valor: object) -> int:
    """Converte contagem de tokens ausente ou ilegivel em zero."""

    return valor if isinstance(valor, int) else 0
