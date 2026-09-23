/**
 * Cliente HTTP do gateway.
 *
 * Ponto unico de saida da aplicacao para a rede. Nenhum componente chama
 * `fetch` diretamente.
 *
 * Responsabilidades:
 *  - ler a URL base de `VITE_API_BASE_URL` (RNF11);
 *  - anexar o token de acesso em toda requisicao autenticada (RF16);
 *  - traduzir o corpo de erro padronizado da plataforma em erro tipado,
 *    conforme `packages/contracts/schemas/error.schema.json`;
 *  - aplicar timeouts distintos: operacoes de CRM seguem o alvo de RNF07,
 *    a estruturacao por IA segue o de RNF06 (ate 15 s);
 *  - redirecionar ao login quando o token expira.
 *
 * Todo erro - da API, de rede, de timeout ou de resposta ilegivel - sai deste
 * modulo como um unico tipo, `ApiError`. Quem chama trata uma coisa so.
 *
 * A URL base ja inclui o prefixo de versao (`/api/v1`), entao os modulos de
 * dominio declaram o caminho relativo a ela: `/demands`, nao `/api/v1/demands`.
 */

import type { ApiErrorDetails, ApiErrorResponse, JsonValue } from '@/types/api';

/** Metodos HTTP usados pela plataforma. */
export type HttpMethod = 'GET' | 'POST' | 'PUT' | 'PATCH' | 'DELETE';

/** Valor aceito em query string. `undefined` e `null` sao omitidos. */
export type QueryValue = string | number | boolean | null | undefined;

/** Parametros de query string de uma requisicao. */
export type QueryParams = Readonly<Record<string, QueryValue>>;

/**
 * Procedencia da falha. Serve para a interface distinguir o que o operador
 * pode resolver (`http`) do que e infraestrutura (`network`, `timeout`).
 */
export type ApiErrorKind = 'http' | 'network' | 'timeout' | 'invalid_response' | 'configuration';

/** Codigos emitidos pelo proprio cliente, quando a falha nao vem da API. */
export const CLIENT_ERROR_CODES = {
  network: 'NETWORK_ERROR',
  timeout: 'REQUEST_TIMEOUT',
  invalidResponse: 'INVALID_RESPONSE',
  missingBaseUrl: 'MISSING_API_BASE_URL',
  http: 'HTTP_ERROR',
} as const;

/**
 * Timeouts, que sao parte do contrato e nao detalhe de implementacao.
 *
 * RNF07 mira 500 ms de resposta no CRM e RNF06 admite ate 15 s na estruturacao
 * por IA. O corte do cliente fica acima do alvo do CRM de proposito: o alvo
 * mede o servico, o timeout protege a tela de ficar presa; cortar em 500 ms
 * transformaria qualquer oscilacao de rede em erro para o operador.
 */
export const TIMEOUTS = {
  /** Operacoes de CRM e pipeline (RNF07). */
  default: 5_000,
  /** Estruturacao por IA (RNF06). */
  ai: 15_000,
} as const;

/** Opcoes de uma requisicao. `TBody` e o corpo enviado, sempre serializado como JSON. */
export interface RequestOptions<TBody = unknown> {
  readonly method?: HttpMethod;
  readonly body?: TBody;
  readonly query?: QueryParams;
  /** Padrao: `TIMEOUTS.default`. Chamadas de IA passam `TIMEOUTS.ai`. */
  readonly timeoutMs?: number;
  /** Cancelamento vindo de quem chama (troca de tela, por exemplo). */
  readonly signal?: AbortSignal;
}

/**
 * Contexto repassado pelos modulos de dominio: cancelamento e, quando a
 * operacao foge do alvo padrao, o timeout.
 */
export type RequestContext = Pick<RequestOptions, 'signal' | 'timeoutMs'>;

/**
 * Erro unico do cliente HTTP.
 *
 * `code` e `message` vem do envelope da plataforma quando a API responde; nas
 * demais falhas sao preenchidos por este modulo, com mensagem em portugues
 * exibivel ao operador e sem detalhe de infraestrutura (RNF10).
 */
export class ApiError extends Error {
  readonly kind: ApiErrorKind;
  readonly code: string;
  readonly status: number | null;
  readonly details: Readonly<Record<string, JsonValue>> | null;
  readonly requestId: string | null;

  constructor(params: {
    kind: ApiErrorKind;
    code: string;
    message: string;
    status?: number | null;
    details?: Readonly<Record<string, JsonValue>> | null;
    requestId?: string | null;
    cause?: unknown;
  }) {
    super(params.message, { cause: params.cause });
    this.name = 'ApiError';
    this.kind = params.kind;
    this.code = params.code;
    this.status = params.status ?? null;
    this.details = params.details ?? null;
    this.requestId = params.requestId ?? null;
  }
}

/** Distingue o erro do cliente HTTP de qualquer outro lancado na aplicacao. */
export function isApiError(value: unknown): value is ApiError {
  return value instanceof ApiError;
}

// ---------------------------------------------------------------------------
// Sessao (RF16)
// ---------------------------------------------------------------------------

let accessToken: string | null = null;
let unauthorizedHandler: (() => void) | null = null;

/** Guarda o token emitido pelo gateway. `null` encerra a sessao em memoria. */
export function setAccessToken(token: string | null): void {
  accessToken = token;
}

/** Token corrente, ou `null` quando nao ha sessao. */
export function getAccessToken(): string | null {
  return accessToken;
}

/**
 * Registra o que fazer quando a API responde 401: o token expirou ou foi
 * revogado. O cliente HTTP nao conhece rotas - quem monta a aplicacao registra
 * aqui o redirecionamento ao login. Retorna a funcao que desfaz o registro.
 */
export function onUnauthorized(handler: () => void): () => void {
  unauthorizedHandler = handler;

  return () => {
    if (unauthorizedHandler === handler) {
      unauthorizedHandler = null;
    }
  };
}

// ---------------------------------------------------------------------------
// URL base (RNF11)
// ---------------------------------------------------------------------------

/**
 * URL base da API, sem barra final.
 *
 * Nao existe valor padrao no codigo de proposito: ambiente sem
 * `VITE_API_BASE_URL` falha na primeira chamada, com mensagem clara, em vez de
 * apontar silenciosamente para o lugar errado.
 */
export function getApiBaseUrl(): string {
  const configured = import.meta.env.VITE_API_BASE_URL;

  if (typeof configured !== 'string' || configured.trim() === '') {
    throw new ApiError({
      kind: 'configuration',
      code: CLIENT_ERROR_CODES.missingBaseUrl,
      message: 'URL da API nao configurada. Defina VITE_API_BASE_URL conforme o .env.example.',
    });
  }

  return configured.trim().replace(/\/+$/, '');
}

function buildUrl(path: string, query?: QueryParams): string {
  const base = getApiBaseUrl();
  const normalizedPath = path.startsWith('/') ? path : `/${path}`;
  const search = new URLSearchParams();

  for (const [key, value] of Object.entries(query ?? {})) {
    if (value !== undefined && value !== null) {
      search.append(key, String(value));
    }
  }

  const queryString = search.toString();

  return queryString === '' ? `${base}${normalizedPath}` : `${base}${normalizedPath}?${queryString}`;
}

// ---------------------------------------------------------------------------
// Leitura do envelope de erro
// ---------------------------------------------------------------------------

function isErrorResponse(value: unknown): value is ApiErrorResponse {
  if (typeof value !== 'object' || value === null || !('error' in value)) {
    return false;
  }

  const candidate: unknown = (value as { error: unknown }).error;

  return (
    typeof candidate === 'object' &&
    candidate !== null &&
    typeof (candidate as ApiErrorDetails).code === 'string' &&
    typeof (candidate as ApiErrorDetails).message === 'string'
  );
}

/** Mensagem generica por familia de status, quando o corpo nao traz envelope. */
function fallbackMessage(status: number): string {
  if (status === 401) return 'Sessao expirada. Entre novamente.';
  if (status === 403) return 'Voce nao tem permissao para esta operacao.';
  if (status === 404) return 'Recurso nao encontrado.';
  if (status === 409) return 'A operacao conflita com o estado atual do recurso.';
  if (status === 422 || status === 400) return 'Dados invalidos para esta operacao.';
  if (status >= 500) return 'O servico esta indisponivel no momento. Tente novamente.';

  return 'Nao foi possivel completar a operacao.';
}

async function readBody(response: Response): Promise<unknown> {
  const text = await response.text();

  if (text.trim() === '') {
    return null;
  }

  try {
    return JSON.parse(text) as unknown;
  } catch {
    return undefined;
  }
}

function toApiError(response: Response, body: unknown, requestId: string | null): ApiError {
  if (isErrorResponse(body)) {
    const { code, message, details, request_id: bodyRequestId } = body.error;

    return new ApiError({
      kind: 'http',
      code,
      message,
      status: response.status,
      details: details ?? null,
      requestId: bodyRequestId ?? requestId,
    });
  }

  return new ApiError({
    kind: 'http',
    code: CLIENT_ERROR_CODES.http,
    message: fallbackMessage(response.status),
    status: response.status,
    requestId,
  });
}

// ---------------------------------------------------------------------------
// Requisicao
// ---------------------------------------------------------------------------

function linkAbort(controller: AbortController, external?: AbortSignal): () => void {
  if (external === undefined) {
    return () => undefined;
  }

  if (external.aborted) {
    controller.abort(external.reason);

    return () => undefined;
  }

  const forward = () => controller.abort(external.reason);
  external.addEventListener('abort', forward);

  return () => external.removeEventListener('abort', forward);
}

/**
 * Executa uma requisicao ao gateway e devolve o corpo ja tipado.
 *
 * `TResponse` e o tipo declarado no contrato para aquela operacao: divergencia
 * entre o que o modulo de dominio promete e o que a tela consome falha na
 * compilacao, nao em producao (RNF02).
 *
 * @throws {ApiError} em qualquer falha - da API, de rede, de timeout ou de
 * resposta ilegivel.
 */
export async function request<TResponse, TBody = unknown>(
  path: string,
  options: RequestOptions<TBody> = {},
): Promise<TResponse> {
  const { method = 'GET', body, query, timeoutMs = TIMEOUTS.default, signal } = options;

  const url = buildUrl(path, query);
  const controller = new AbortController();
  const unlink = linkAbort(controller, signal);
  const timedOut = { value: false };
  const timer = setTimeout(() => {
    timedOut.value = true;
    controller.abort();
  }, timeoutMs);

  const headers: Record<string, string> = { Accept: 'application/json' };

  if (body !== undefined) {
    headers['Content-Type'] = 'application/json';
  }

  if (accessToken !== null) {
    headers.Authorization = `Bearer ${accessToken}`;
  }

  let response: Response;

  try {
    response = await fetch(url, {
      method,
      headers,
      signal: controller.signal,
      body: body === undefined ? undefined : JSON.stringify(body),
    });
  } catch (cause) {
    if (timedOut.value) {
      throw new ApiError({
        kind: 'timeout',
        code: CLIENT_ERROR_CODES.timeout,
        message: 'O servico demorou mais que o esperado para responder. Tente novamente.',
        cause,
      });
    }

    if (signal?.aborted === true) {
      // Cancelamento pedido por quem chama nao e falha: propaga como veio, para
      // que o cache de dados o reconheca e nao exiba erro ao operador.
      throw cause;
    }

    throw new ApiError({
      kind: 'network',
      code: CLIENT_ERROR_CODES.network,
      message: 'Nao foi possivel falar com o servidor. Verifique sua conexao.',
      cause,
    });
  } finally {
    clearTimeout(timer);
    unlink();
  }

  const requestId = response.headers.get('X-Request-ID');
  const payload = await readBody(response);

  if (!response.ok) {
    if (response.status === 401) {
      accessToken = null;
      unauthorizedHandler?.();
    }

    throw toApiError(response, payload, requestId);
  }

  if (payload === undefined) {
    throw new ApiError({
      kind: 'invalid_response',
      code: CLIENT_ERROR_CODES.invalidResponse,
      message: 'O servico devolveu uma resposta em formato inesperado.',
      status: response.status,
      requestId,
    });
  }

  // 204 e corpo vazio sao respostas validas de operacoes sem retorno; a
  // operacao que as usa declara `void` como `TResponse`.
  return payload as TResponse;
}

/** Atalhos por metodo. Existem para os modulos de dominio ficarem legiveis. */
export const api = {
  get: <TResponse>(path: string, options?: Omit<RequestOptions, 'method' | 'body'>) =>
    request<TResponse>(path, { ...options, method: 'GET' }),

  post: <TResponse, TBody>(
    path: string,
    body: TBody,
    options?: Omit<RequestOptions<TBody>, 'method' | 'body'>,
  ) => request<TResponse, TBody>(path, { ...options, method: 'POST', body }),

  put: <TResponse, TBody>(
    path: string,
    body: TBody,
    options?: Omit<RequestOptions<TBody>, 'method' | 'body'>,
  ) => request<TResponse, TBody>(path, { ...options, method: 'PUT', body }),

  patch: <TResponse, TBody>(
    path: string,
    body: TBody,
    options?: Omit<RequestOptions<TBody>, 'method' | 'body'>,
  ) => request<TResponse, TBody>(path, { ...options, method: 'PATCH', body }),

  delete: <TResponse = void>(path: string, options?: Omit<RequestOptions, 'method' | 'body'>) =>
    request<TResponse>(path, { ...options, method: 'DELETE' }),
} as const;
