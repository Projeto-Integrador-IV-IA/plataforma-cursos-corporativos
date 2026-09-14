/**
 * Caminhos da aplicacao em um unico lugar.
 *
 * Nenhum componente escreve URL literal: quem navega importa daqui. Isso evita
 * link quebrado silencioso quando uma rota muda e mantem o mapa de navegacao
 * conferivel contra `routes.tsx`.
 */

export const PATHS = {
  login: '/login',
  clients: '/clientes',
  clientDetail: '/clientes/:clientId',
  demands: '/demandas',
  demandDetail: '/demandas/:demandId',
  demandIngestion: '/demandas/:demandId/ingestao',
  demandStructuring: '/demandas/:demandId/estruturacao',
  artifactVersions: '/artefatos/:artifactId/versoes',
} as const;

/** Constroi o caminho de uma tela que depende de identificador. */
export const buildPath = {
  clientDetail: (clientId: string): string => `/clientes/${clientId}`,
  demandDetail: (demandId: string): string => `/demandas/${demandId}`,
  demandIngestion: (demandId: string): string => `/demandas/${demandId}/ingestao`,
  demandStructuring: (demandId: string): string => `/demandas/${demandId}/estruturacao`,
  artifactVersions: (artifactId: string): string => `/artefatos/${artifactId}/versoes`,
} as const;
