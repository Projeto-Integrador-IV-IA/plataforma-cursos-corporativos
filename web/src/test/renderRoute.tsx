/**
 * Helper de renderizacao de rota para os testes.
 *
 * Monta o mesmo array `routes` exportado por `app/routes.tsx`, porem sobre
 * `MemoryRouter` + `useRoutes` em vez de `createMemoryRouter`. Motivo: o data
 * router constroi um `Request` a cada navegacao, e o `Request` do Node recusa o
 * `AbortSignal` do jsdom, quebrando qualquer teste que clique em um link.
 *
 * O casamento de rotas, o aninhamento, os parametros e o splat sao os mesmos
 * nos dois modos. A diferenca aparece se alguma rota passar a usar recurso
 * exclusivo do data router (`loader`, `action`, `errorElement`): nesse dia este
 * helper precisa voltar para `createMemoryRouter`, com o ambiente ajustado.
 */

import { render } from '@testing-library/react';
import { MemoryRouter, useRoutes } from 'react-router-dom';

import { Providers } from '@/app/providers';
import { routes } from '@/app/routes';

function RoutedApp() {
  return useRoutes(routes);
}

export function renderRoute(initialPath: string) {
  return render(
    <Providers>
      <MemoryRouter
        initialEntries={[initialPath]}
        future={{ v7_startTransition: true, v7_relativeSplatPath: true }}
      >
        <RoutedApp />
      </MemoryRouter>
    </Providers>,
  );
}
