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
  clientNew: '/clientes/novo',
  clientDetail: '/clientes/:clientId',
  demands: '/demandas',
  demandNew: '/demandas/nova',
  demandDetail: '/demandas/:demandId',
  demandIngestion: '/demandas/:demandId/ingestao',
  demandStructuring: '/demandas/:demandId/estruturacao',
  artifactVersions: '/artefatos/:artifactId/versoes',
} as const;

/**
 * Parametros de query string que fazem parte do endereco de uma tela.
 *
 * Ficam aqui pelo mesmo motivo dos caminhos: quem le o endereco e quem o
 * escreve precisam concordar sobre o nome. A execucao acompanhada na revisao
 * da estruturacao vai na URL para sobreviver a um recarregamento - o estado da
 * execucao e consultado por identificador (RF24), e perde-lo deixaria o
 * operador sem saber se ainda ha algo em curso.
 */
export const QUERY_PARAMS = {
  structuringJob: 'execucao',
} as const;

/** Constroi o caminho de uma tela que depende de identificador. */
export const buildPath = {
  clientDetail: (clientId: string): string => `/clientes/${clientId}`,
  demandDetail: (demandId: string): string => `/demandas/${demandId}`,
  demandIngestion: (demandId: string): string => `/demandas/${demandId}/ingestao`,
  demandStructuring: (demandId: string): string => `/demandas/${demandId}/estruturacao`,
  artifactVersions: (artifactId: string): string => `/artefatos/${artifactId}/versoes`,
} as const;
