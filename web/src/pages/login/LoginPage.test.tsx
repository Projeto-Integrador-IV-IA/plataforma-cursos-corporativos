/** Criterios de aceite da tela de login (RF26). */

import { screen, waitFor } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';

import { PATHS } from '@/app/paths';
import { logout } from '@/services/auth';
import { renderRoute } from '@/test/renderRoute';

const BASE_URL = 'https://gateway.test/api/v1';

beforeEach(() => {
  vi.stubEnv('VITE_API_BASE_URL', BASE_URL);
  logout();
});

afterEach(() => {
  logout();
  vi.unstubAllGlobals();
  vi.unstubAllEnvs();
});

describe('tela de login', () => {
  it('valida os dois campos obrigatorios antes de chamar o gateway', async () => {
    const fetchDouble = vi.fn();
    vi.stubGlobal('fetch', fetchDouble);
    const user = userEvent.setup();
    renderRoute(PATHS.login, { authenticated: false });

    await user.click(screen.getByRole('button', { name: 'Entrar' }));

    expect(screen.getByText('Informe o e-mail.')).toBeDefined();
    expect(screen.getByText('Informe a senha.')).toBeDefined();
    expect(fetchDouble).not.toHaveBeenCalled();
  });

  it('volta ao destino pretendido depois do login bem-sucedido', async () => {
    vi.stubGlobal('fetch', (input: RequestInfo | URL) => {
      const url = String(input);
      if (url.endsWith('/auth/login')) {
        return Promise.resolve(
          new Response(
            JSON.stringify({
              access_token: 'jwt-secreto',
              token_type: 'bearer',
              expires_in: 120,
              operator: {
                id: '11111111-1111-4111-8111-111111111111',
                name: 'Operadora Teste',
                email: 'operadora@example.com',
                role: 'OPERADOR',
              },
            }),
            { status: 200, headers: { 'Content-Type': 'application/json' } },
          ),
        );
      }

      return Promise.resolve(
        new Response(JSON.stringify({ items: [], total: 0, page: 1, size: 20 }), {
          status: 200,
          headers: { 'Content-Type': 'application/json' },
        }),
      );
    });
    const user = userEvent.setup();
    renderRoute('/demandas?status=ABERTA', { authenticated: false });

    expect(screen.getByRole('heading', { level: 1, name: 'Entrar' })).toBeDefined();
    await user.type(screen.getByLabelText(/E-mail/), 'operadora@example.com');
    await user.type(screen.getByLabelText(/Senha/), 'senha-forte');
    await user.click(screen.getByRole('button', { name: 'Entrar' }));

    await waitFor(() =>
      expect(screen.getByRole('heading', { level: 1, name: 'Demandas' })).toBeDefined(),
    );
  });
});
