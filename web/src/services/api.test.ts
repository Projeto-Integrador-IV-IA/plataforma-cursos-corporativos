/**
 * Cobre os criterios de aceite de RNF02 no cliente HTTP:
 * o caminho feliz, o envelope de erro da plataforma tratado em um unico lugar,
 * a falha de rede e a URL base vinda do ambiente.
 *
 * O `fetch` e substituido por um dublo que registra a requisicao: e assim que
 * verificamos URL, cabecalhos e corpo sem subir servidor.
 */

import { afterEach, describe, expect, it, vi } from 'vitest';

import {
  ApiError,
  CLIENT_ERROR_CODES,
  getApiBaseUrl,
  isApiError,
  onUnauthorized,
  request,
  setAccessToken,
} from '@/services/api';

const BASE_URL = 'https://gateway.test/api/v1';

interface CapturedRequest {
  readonly url: string;
  readonly init: RequestInit | undefined;
}

const captured: CapturedRequest[] = [];

/** Substitui o `fetch` global por um dublo que registra o que foi enviado. */
function stubFetch(responder: (req: CapturedRequest) => Promise<Response>): void {
  const fetchDouble = vi.fn((input: RequestInfo | URL, init?: RequestInit) => {
    const req: CapturedRequest = { url: String(input), init };
    captured.push(req);

    return responder(req);
  });

  vi.stubGlobal('fetch', fetchDouble);
}

/** Resposta JSON pronta, no formato que o gateway devolve. */
function jsonResponse(body: unknown, status = 200, headers: Record<string, string> = {}): Response {
  return new Response(JSON.stringify(body), {
    status,
    headers: { 'Content-Type': 'application/json', ...headers },
  });
}

function firstRequest(): CapturedRequest {
  const req = captured[0];

  if (req === undefined) {
    throw new Error('Nenhuma requisicao foi capturada.');
  }

  return req;
}

function headerOf(req: CapturedRequest, name: string): string | null {
  return new Headers(req.init?.headers).get(name);
}

afterEach(() => {
  captured.length = 0;
  setAccessToken(null);
  vi.unstubAllGlobals();
  vi.unstubAllEnvs();
});

describe('URL base', () => {
  it('vem do ambiente, sem barra final', () => {
    vi.stubEnv('VITE_API_BASE_URL', `${BASE_URL}/`);

    expect(getApiBaseUrl()).toBe(BASE_URL);
  });

  it('falha com erro de configuracao quando a variavel nao esta definida', () => {
    vi.stubEnv('VITE_API_BASE_URL', '');

    expect(() => getApiBaseUrl()).toThrowError(ApiError);
    try {
      getApiBaseUrl();
    } catch (erro) {
      expect(isApiError(erro) && erro.code).toBe(CLIENT_ERROR_CODES.missingBaseUrl);
    }
  });
});

describe('caminho feliz', () => {
  it('monta a URL a partir da base, do caminho e da query, ignorando valor ausente', async () => {
    vi.stubEnv('VITE_API_BASE_URL', BASE_URL);
    stubFetch(() => Promise.resolve(jsonResponse({ items: [], total: 0, page: 1, size: 20 })));

    await request('/demands', { query: { status: 'ABERTA', client_id: undefined, page: 1 } });

    expect(firstRequest().url).toBe(`${BASE_URL}/demands?status=ABERTA&page=1`);
  });

  it('devolve o corpo ja desserializado', async () => {
    vi.stubEnv('VITE_API_BASE_URL', BASE_URL);
    stubFetch(() => Promise.resolve(jsonResponse({ id: 'abc', title: 'Curso de lideranca' }, 201)));

    const criada = await request<{ id: string; title: string }>('/demands', {
      method: 'POST',
      body: { client_id: 'cli-1', title: 'Curso de lideranca' },
    });

    expect(criada).toEqual({ id: 'abc', title: 'Curso de lideranca' });
    expect(firstRequest().init?.method).toBe('POST');
    expect(firstRequest().init?.body).toBe(
      JSON.stringify({ client_id: 'cli-1', title: 'Curso de lideranca' }),
    );
    expect(headerOf(firstRequest(), 'Content-Type')).toBe('application/json');
  });

  it('anexa o token de acesso quando ha sessao (RF16)', async () => {
    vi.stubEnv('VITE_API_BASE_URL', BASE_URL);
    stubFetch(() => Promise.resolve(jsonResponse({ ok: true })));
    setAccessToken('token-123');

    await request('/demands');

    expect(headerOf(firstRequest(), 'Authorization')).toBe('Bearer token-123');
  });

  it('nao anexa Authorization quando nao ha sessao', async () => {
    vi.stubEnv('VITE_API_BASE_URL', BASE_URL);
    stubFetch(() => Promise.resolve(jsonResponse({ ok: true })));

    await request('/demands');

    expect(headerOf(firstRequest(), 'Authorization')).toBeNull();
  });
});

describe('erro da API no envelope da plataforma', () => {
  it('traduz codigo, mensagem, detalhes e correlacao', async () => {
    vi.stubEnv('VITE_API_BASE_URL', BASE_URL);
    stubFetch(() =>
      Promise.resolve(
        jsonResponse(
          {
            error: {
              code: 'INVALID_STAGE_TRANSITION',
              message: 'Nao e possivel avancar de captacao para proposta.',
              details: { from: 'CAPTACAO', to: 'PROPOSTA' },
              request_id: '0f3c',
            },
          },
          409,
        ),
      ),
    );

    const erro = await request('/demands/abc/transitions', { method: 'POST', body: {} }).catch(
      (motivo: unknown) => motivo,
    );

    expect(isApiError(erro)).toBe(true);
    if (!isApiError(erro)) return;
    expect(erro.kind).toBe('http');
    expect(erro.status).toBe(409);
    expect(erro.code).toBe('INVALID_STAGE_TRANSITION');
    expect(erro.message).toBe('Nao e possivel avancar de captacao para proposta.');
    expect(erro.details).toEqual({ from: 'CAPTACAO', to: 'PROPOSTA' });
    expect(erro.requestId).toBe('0f3c');
  });

  it('usa mensagem generica quando o corpo nao segue o envelope', async () => {
    vi.stubEnv('VITE_API_BASE_URL', BASE_URL);
    stubFetch(() => Promise.resolve(new Response('<html>Bad Gateway</html>', { status: 502 })));

    const erro = await request('/demands').catch((motivo: unknown) => motivo);

    expect(isApiError(erro)).toBe(true);
    if (!isApiError(erro)) return;
    expect(erro.code).toBe(CLIENT_ERROR_CODES.http);
    expect(erro.status).toBe(502);
    expect(erro.message).toContain('indisponivel');
  });

  it('le a correlacao do cabecalho quando o corpo nao a traz (RNF09)', async () => {
    vi.stubEnv('VITE_API_BASE_URL', BASE_URL);
    stubFetch(() =>
      Promise.resolve(
        jsonResponse({ error: { code: 'DEMAND_NOT_FOUND', message: 'Demanda inexistente.' } }, 404, {
          'X-Request-ID': 'req-42',
        }),
      ),
    );

    const erro = await request('/demands/abc').catch((motivo: unknown) => motivo);

    expect(isApiError(erro) && erro.requestId).toBe('req-42');
  });

  it('encerra a sessao e avisa quem cuida do login quando o token expira (401)', async () => {
    vi.stubEnv('VITE_API_BASE_URL', BASE_URL);
    stubFetch(() =>
      Promise.resolve(
        jsonResponse({ error: { code: 'UNAUTHENTICATED', message: 'Sessao expirada.' } }, 401),
      ),
    );
    setAccessToken('token-expirado');
    const aoExpirar = vi.fn();
    const cancelarRegistro = onUnauthorized(aoExpirar);

    await request('/demands').catch(() => undefined);

    expect(aoExpirar).toHaveBeenCalledTimes(1);
    cancelarRegistro();

    await request('/demands').catch(() => undefined);

    expect(aoExpirar).toHaveBeenCalledTimes(1);
  });
});

describe('falhas fora da API', () => {
  it('traduz erro de rede em ApiError sem expor detalhe interno (RNF10)', async () => {
    vi.stubEnv('VITE_API_BASE_URL', BASE_URL);
    const causa = new TypeError('Failed to fetch');
    stubFetch(() => Promise.reject(causa));

    const erro = await request('/demands').catch((motivo: unknown) => motivo);

    expect(isApiError(erro)).toBe(true);
    if (!isApiError(erro)) return;
    expect(erro.kind).toBe('network');
    expect(erro.code).toBe(CLIENT_ERROR_CODES.network);
    expect(erro.status).toBeNull();
    expect(erro.message).not.toContain('Failed to fetch');
    expect(erro.cause).toBe(causa);
  });

  it('corta a requisicao quando o servico nao responde no prazo (RNF06, RNF07)', async () => {
    vi.stubEnv('VITE_API_BASE_URL', BASE_URL);
    stubFetch(
      (req) =>
        new Promise((_, rejeitar) => {
          req.init?.signal?.addEventListener('abort', () => {
            rejeitar(new DOMException('The operation was aborted.', 'AbortError'));
          });
        }),
    );

    const erro = await request('/structuring', { timeoutMs: 10 }).catch(
      (motivo: unknown) => motivo,
    );

    expect(isApiError(erro)).toBe(true);
    if (!isApiError(erro)) return;
    expect(erro.kind).toBe('timeout');
    expect(erro.code).toBe(CLIENT_ERROR_CODES.timeout);
  });

  it('rejeita resposta que nao e JSON valido', async () => {
    vi.stubEnv('VITE_API_BASE_URL', BASE_URL);
    stubFetch(() =>
      Promise.resolve(
        new Response('nao e json', {
          status: 200,
          headers: { 'Content-Type': 'application/json' },
        }),
      ),
    );

    const erro = await request('/demands').catch((motivo: unknown) => motivo);

    expect(isApiError(erro) && erro.kind).toBe('invalid_response');
  });

  it('propaga o cancelamento de quem chamou sem transforma-lo em erro da API', async () => {
    vi.stubEnv('VITE_API_BASE_URL', BASE_URL);
    stubFetch(
      (req) =>
        new Promise((_, rejeitar) => {
          req.init?.signal?.addEventListener('abort', () => {
            rejeitar(new DOMException('The operation was aborted.', 'AbortError'));
          });
        }),
    );
    const controle = new AbortController();
    const promessa = request('/demands', { signal: controle.signal }).catch(
      (motivo: unknown) => motivo,
    );
    controle.abort();

    expect(isApiError(await promessa)).toBe(false);
  });
});
