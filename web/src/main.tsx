/**
 * Ponto de entrada do frontend.
 *
 * Monta a aplicacao na raiz do documento, envolvendo o roteador nos providers
 * globais e importando os estilos.
 */

import { StrictMode } from 'react';
import { createRoot } from 'react-dom/client';
import { RouterProvider, createBrowserRouter } from 'react-router-dom';

import { Providers } from '@/app/providers';
import { routes } from '@/app/routes';
import '@/styles/global.css';

const container = document.getElementById('root');

if (!container) {
  throw new Error('Elemento #root nao encontrado em index.html.');
}

// Flags do React Router v7 ligadas desde ja: evitam divergencia de
// comportamento na migracao e silenciam os avisos de futuro em execucao.
// `v7_startTransition` pertence ao RouterProvider, nao ao roteador.
const router = createBrowserRouter(routes, {
  future: { v7_relativeSplatPath: true },
});

createRoot(container).render(
  <StrictMode>
    <Providers>
      <RouterProvider router={router} future={{ v7_startTransition: true }} />
    </Providers>
  </StrictMode>,
);
