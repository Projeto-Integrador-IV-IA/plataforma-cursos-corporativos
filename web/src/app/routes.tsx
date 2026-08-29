/**
 * Mapa de rotas da aplicacao.
 *
 * Rotas previstas:
 *   /login                        autenticacao (RF16)
 *   /clientes                     lista e cadastro de clientes (RF01, RF03)
 *   /clientes/:clientId           detalhe do cliente
 *   /demandas                     lista com filtro por status, cliente, periodo (RF02, RF03)
 *   /demandas/:demandId           detalhe: pipeline, historico e artefatos (RF04, RF05, RF06)
 *   /demandas/:demandId/ingestao  entrada de demanda bruta (RF09)
 *   /demandas/:demandId/estruturacao  revisao da saida da IA antes de uso externo (RF14)
 *   /artefatos/:artifactId/versoes    historico de versoes (RF08)
 *
 * Toda rota, exceto /login, exige sessao autenticada (RNF10). A arvore ja
 * separa as duas familias: `/login` e rota irma, e as demais sao filhas do
 * layout `App`.
 *
 * TODO(RF16): envolver o elemento do layout no guarda de sessao quando a
 * autenticacao existir. Enquanto o gateway nao emite token, nao ha sessao para
 * verificar e as rotas ficam abertas.
 */

import { Navigate, type RouteObject } from 'react-router-dom';

import { App } from '@/app/App';
import { PATHS } from '@/app/paths';
import { ArtifactVersionsPage } from '@/pages/artifact-versions/ArtifactVersionsPage';
import { ClientDetailPage } from '@/pages/client-detail/ClientDetailPage';
import { ClientsPage } from '@/pages/clients/ClientsPage';
import { DemandDetailPage } from '@/pages/demand-detail/DemandDetailPage';
import { DemandIngestionPage } from '@/pages/demand-ingestion/DemandIngestionPage';
import { DemandStructuringPage } from '@/pages/demand-structuring/DemandStructuringPage';
import { DemandsPage } from '@/pages/demands/DemandsPage';
import { LoginPage } from '@/pages/login/LoginPage';
import { NotFoundPage } from '@/pages/not-found/NotFoundPage';

export const routes: RouteObject[] = [
  {
    path: PATHS.login,
    element: <LoginPage />,
  },
  {
    path: '/',
    element: <App />,
    children: [
      { index: true, element: <Navigate to={PATHS.clients} replace /> },
      { path: PATHS.clients, element: <ClientsPage /> },
      { path: PATHS.clientDetail, element: <ClientDetailPage /> },
      { path: PATHS.demands, element: <DemandsPage /> },
      { path: PATHS.demandDetail, element: <DemandDetailPage /> },
      { path: PATHS.demandIngestion, element: <DemandIngestionPage /> },
      { path: PATHS.demandStructuring, element: <DemandStructuringPage /> },
      { path: PATHS.artifactVersions, element: <ArtifactVersionsPage /> },
      { path: '*', element: <NotFoundPage /> },
    ],
  },
];
