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
  pipeline: '/pipeline',
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
 * vai na URL para sobreviver a um recarregamento; os identificadores da fonte
 * e do trecho tambem permitem abrir diretamente uma evidencia.
 */
export const QUERY_PARAMS = {
  structuringJob: 'execucao',
  sourceId: 'fonte',
  sourceSegmentId: 'trecho',
} as const;

/** Constroi o caminho de uma tela que depende de identificador. */
export const buildPath = {
  clientDetail: (clientId: string): string => `/clientes/${clientId}`,
  demandDetail: (demandId: string): string => `/demandas/${demandId}`,
  demandEvidence: (demandId: string, sourceId: string, segmentId: string): string => {
    const query = new URLSearchParams({
      [QUERY_PARAMS.sourceId]: sourceId,
      [QUERY_PARAMS.sourceSegmentId]: segmentId,
    });

    return `/demandas/${demandId}?${query.toString()}#source-evidence`;
  },
  demandIngestion: (demandId: string): string => `/demandas/${demandId}/ingestao`,
  demandStructuring: (demandId: string): string => `/demandas/${demandId}/estruturacao`,
  artifactVersions: (artifactId: string): string => `/artefatos/${artifactId}/versoes`,
} as const;
