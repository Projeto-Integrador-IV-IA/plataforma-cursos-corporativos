/** Contrato da sessao do frontend com o gateway (RF26). */

import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';

import { getAccessToken } from '@/services/api';
import { getAuthSession, login, logout } from '@/services/auth';

const BASE_URL = 'https://gateway.test/api/v1';

const TOKEN_RESPONSE = {
  access_token: 'jwt-secreto',
  token_type: 'bearer',
  expires_in: 120,
  operator: {
    id: '11111111-1111-4111-8111-111111111111',
    name: 'Operadora Teste',
    email: 'operadora@example.com',
    role: 'OPERADOR',
  },
} as const;

beforeEach(() => {
  vi.stubEnv('VITE_API_BASE_URL', BASE_URL);
  window.sessionStorage.clear();
  logout();
});

afterEach(() => {
  logout();
  vi.unstubAllGlobals();
  vi.unstubAllEnvs();
});

describe('sessao do operador', () => {
  it('troca credenciais pelo token e persiste a sessao somente na aba', async () => {
    const fetchDouble = vi.fn((input: RequestInfo | URL, init?: RequestInit) => {
      void input;
      void init;

      return Promise.resolve(
        new Response(JSON.stringify(TOKEN_RESPONSE), {
          status: 200,
          headers: { 'Content-Type': 'application/json' },
        }),
      );
    });
    vi.stubGlobal('fetch', fetchDouble);

    const session = await login({
      email: 'operadora@example.com',
      password: 'senha-forte',
    });

    expect(session.operator.name).toBe('Operadora Teste');
    expect(getAccessToken()).toBe(TOKEN_RESPONSE.access_token);
    expect(getAuthSession()).toEqual(session);
    expect(window.localStorage.length).toBe(0);
    expect(window.sessionStorage.length).toBe(1);

    const [url, init] = fetchDouble.mock.calls[0] ?? [];
    expect(url).toBe(`${BASE_URL}/auth/login`);
    expect(String(url)).not.toContain(TOKEN_RESPONSE.access_token);
    expect(init?.body).toBe(
      JSON.stringify({
        email: 'operadora@example.com',
        password: 'senha-forte',
      }),
    );
  });

  it('logout remove token e dados persistidos', async () => {
    vi.stubGlobal('fetch', () =>
      Promise.resolve(
        new Response(JSON.stringify(TOKEN_RESPONSE), {
          status: 200,
          headers: { 'Content-Type': 'application/json' },
        }),
      ),
    );
    await login({ email: 'operadora@example.com', password: 'senha-forte' });

    logout();

    expect(getAccessToken()).toBeNull();
    expect(getAuthSession()).toBeNull();
    expect(window.sessionStorage.length).toBe(0);
  });
});
