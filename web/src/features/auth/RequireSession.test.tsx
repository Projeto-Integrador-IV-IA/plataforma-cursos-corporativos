/** Redirecionamento central quando uma chamada autenticada devolve 401. */

import { screen, waitFor } from '@testing-library/react';
import { afterEach, describe, expect, it, vi } from 'vitest';

import { PATHS } from '@/app/paths';
import { request, setAccessToken } from '@/services/api';
import { logout } from '@/services/auth';
import { renderRoute } from '@/test/renderRoute';

afterEach(() => {
  logout();
  vi.unstubAllGlobals();
  vi.unstubAllEnvs();
});

describe('sessao expirada', () => {
  it('401 encerra a sessao e volta ao login com mensagem', async () => {
    vi.stubEnv('VITE_API_BASE_URL', 'https://gateway.test/api/v1');
    vi.stubGlobal('fetch', () =>
      Promise.resolve(
        new Response(
          JSON.stringify({
            error: { code: 'UNAUTHENTICATED', message: 'Sessao expirada.' },
          }),
          { status: 401, headers: { 'Content-Type': 'application/json' } },
        ),
      ),
    );
    renderRoute(PATHS.clients);
    setAccessToken('token-expirado');

    await request('/auth/verify').catch(() => undefined);

    await waitFor(() =>
      expect(screen.getByRole('heading', { level: 1, name: 'Entrar' })).toBeDefined(),
    );
    expect(screen.getByRole('alert').textContent).toContain('sessao expirou');
  });
});
