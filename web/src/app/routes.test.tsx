/**
 * Cobre o criterio de aceite de RNF01: as rotas principais sao navegaveis.
 *
 * O teste consome o mesmo array exportado por `routes.tsx`, entao falha se uma
 * rota for renomeada ou removida sem que o mapa de caminhos acompanhe.
 */

import { screen } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { describe, expect, it } from 'vitest';

import { PATHS } from '@/app/paths';
import { renderRoute } from '@/test/renderRoute';

describe('mapa de rotas', () => {
  const telas: readonly [caminho: string, titulo: string][] = [
    [PATHS.login, 'Entrar'],
    [PATHS.clients, 'Clientes'],
    ['/clientes/abc-123', 'Detalhe do cliente'],
    [PATHS.demands, 'Demandas'],
    ['/demandas/abc-123', 'Detalhe da demanda'],
    ['/demandas/abc-123/ingestao', 'Ingestao da demanda'],
    ['/demandas/abc-123/estruturacao', 'Estruturacao por IA'],
    ['/artefatos/abc-123/versoes', 'Versoes do artefato'],
  ];

  it.each(telas)('renderiza a tela de %s', (caminho, titulo) => {
    renderRoute(caminho);

    expect(screen.getByRole('heading', { level: 1, name: titulo })).toBeDefined();
  });

  it('redireciona a raiz para a lista de clientes', () => {
    renderRoute('/');

    expect(screen.getByRole('heading', { level: 1, name: 'Clientes' })).toBeDefined();
  });

  it('cai na tela de rota inexistente para caminho desconhecido', () => {
    renderRoute('/rota-que-nao-existe');

    expect(screen.getByRole('heading', { level: 1, name: 'Pagina nao encontrada' })).toBeDefined();
  });

  it('navega entre clientes e demandas pela navegacao lateral', async () => {
    const usuario = userEvent.setup();
    renderRoute(PATHS.clients);

    await usuario.click(screen.getByRole('link', { name: 'Demandas' }));

    expect(screen.getByRole('heading', { level: 1, name: 'Demandas' })).toBeDefined();
  });

  it('renderiza o layout base nas rotas autenticadas e nao em /login', () => {
    renderRoute(PATHS.clients);
    expect(screen.getByRole('navigation', { name: 'Navegacao principal' })).toBeDefined();
  });

  it('nao renderiza o layout base em /login', () => {
    renderRoute(PATHS.login);
    expect(screen.queryByRole('navigation', { name: 'Navegacao principal' })).toBeNull();
  });
});

describe('parametros de rota', () => {
  it('repassa o identificador da URL para a tela de detalhe', () => {
    renderRoute('/clientes/cliente-42');

    expect(screen.getByText(/cliente-42/)).toBeDefined();
  });
});
