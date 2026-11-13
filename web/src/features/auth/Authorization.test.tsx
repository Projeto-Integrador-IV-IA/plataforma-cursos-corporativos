import { render, screen } from '@testing-library/react';
import { afterEach, describe, expect, it, vi } from 'vitest';

import {
  AuthSessionProvider,
  hasPermission,
  PermissionGate,
  PERMISSIONS,
} from '@/features/auth/Authorization';
import { login, logout, type AuthSession } from '@/services/auth';
import { renderRoute } from '@/test/renderRoute';

afterEach(() => {
  logout();
  vi.unstubAllGlobals();
  vi.unstubAllEnvs();
});

function session(role: string): AuthSession {
  return {
    accessToken: 'test-token',
    expiresAt: Date.now() + 60_000,
    operator: {
      id: 'test-operator',
      name: 'Operador de teste',
      email: 'operador@example.com',
      role,
    },
  };
}

describe('autorizacao visual por perfil', () => {
  it('mantem as permissoes atuais de OPERADOR e nega por padrao perfis sem matriz', () => {
    expect(hasPermission('OPERADOR', PERMISSIONS.demandsManage)).toBe(true);
    expect(hasPermission('REVISOR', PERMISSIONS.demandsManage)).toBe(false);
    expect(hasPermission('toString', PERMISSIONS.demandsManage)).toBe(false);
    expect(hasPermission(undefined, PERMISSIONS.demandsManage)).toBe(false);
  });

  it('esconde a acao quando o perfil nao tem a permissao', () => {
    render(
      <AuthSessionProvider session={session('REVISOR')}>
        <PermissionGate permission={PERMISSIONS.clientsManage}>
          <button type="button">Cadastrar cliente</button>
        </PermissionGate>
      </AuthSessionProvider>,
    );

    expect(screen.queryByRole('button', { name: 'Cadastrar cliente' })).toBeNull();
  });

  it('esconde navegacao e bloqueia acesso direto a rota sem permissao', () => {
    renderRoute('/clientes/novo', { role: 'REVISOR' });

    expect(screen.getByRole('heading', { level: 1, name: 'Acesso nao autorizado' })).toBeDefined();
    expect(screen.queryByRole('link', { name: 'Clientes' })).toBeNull();
    expect(screen.getByText(/nao substitui a autorizacao feita pelo servidor/i)).toBeDefined();
  });

  it('mantem a rota e as acoes do perfil OPERADOR', () => {
    renderRoute('/clientes', { role: 'OPERADOR' });

    expect(screen.getByRole('heading', { level: 1, name: 'Clientes' })).toBeDefined();
    expect(screen.getByRole('link', { name: 'Cadastrar cliente' })).toBeDefined();
  });

  it('le o perfil armazenado pela sessao iniciada no login', async () => {
    vi.stubEnv('VITE_API_BASE_URL', 'https://gateway.test/api/v1');
    vi.stubGlobal(
      'fetch',
      () =>
        Promise.resolve(
          new Response(
            JSON.stringify({
              access_token: 'test-token',
              expires_in: 60,
              operator: {
                id: 'test-operator',
                name: 'Operador de teste',
                email: 'operador@example.com',
                role: 'OPERADOR',
              },
            }),
            { status: 200, headers: { 'Content-Type': 'application/json' } },
          ),
        ),
    );

    await login({ email: 'operador@example.com', password: 'senha' });

    render(
      <PermissionGate permission={PERMISSIONS.clientsManage}>
        <button type="button">Cadastrar cliente</button>
      </PermissionGate>,
    );

    expect(screen.getByRole('button', { name: 'Cadastrar cliente' })).toBeDefined();
  });
});
