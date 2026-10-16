/**
 * Chamadas ao gateway para este dominio.
 *
 * Cada funcao corresponde a uma operacao declarada no contrato OpenAPI
 * (packages/contracts/openapi/). Tipos de entrada e saida vivem em `src/types`
 * e derivam do mesmo contrato (RNF02).
 *
 * Estado do contrato: `GET /api/v1/demands/{demand_id}/artifacts` ja esta
 * declarada em `pipeline-service.yaml` e `listArtifacts` espelha o que ela
 * devolve. Os caminhos por artefato (`/artifacts/...`) seguem PREVISTOS: as
 * convencoes de docs/02-arquitetura/contratos-api.md e o dicionario de dados
 * valem ate o contrato publica-los.
 */

import { api, type RequestContext } from '@/services/api';
import type {
  Artifact,
  ArtifactResultRead,
  ArtifactVersion,
  ArtifactVersionCreate,
  Page,
  PageParams,
  Uuid,
} from '@/types/api';

const DEMANDS = '/demands';
const ARTIFACTS = '/artifacts';

/**
 * Lista os resultados anexados a uma demanda, com as fontes que originaram
 * cada um e suas versoes (RF13, RF15, RF19).
 *
 * A resposta e uma lista simples, e nao um envelope `Page`: a operacao nao
 * pagina nem aceita filtro por tipo. Enquanto o contrato nao estava publicado
 * este modulo prometia `Page<Artifact>` e enviava `page`/`size`/`type`; o
 * servico descartaria os parametros e a tela leria `items` de um array, que
 * viria sempre vazio.
 */
export function listArtifacts(
  demandId: Uuid,
  context: RequestContext = {},
): Promise<readonly ArtifactResultRead[]> {
  return api.get<readonly ArtifactResultRead[]>(`${DEMANDS}/${demandId}/artifacts`, context);
}

/** Busca um artefato pelo identificador. */
export function getArtifact(artifactId: Uuid, context: RequestContext = {}): Promise<Artifact> {
  return api.get<Artifact>(`${ARTIFACTS}/${artifactId}`, context);
}

/**
 * Lista as versoes de um artefato, da mais recente para a mais antiga (RF08).
 *
 * Append-only: editar cria versao nova e as anteriores continuam recuperaveis
 * (RNF09).
 */
export function listArtifactVersions(
  artifactId: Uuid,
  params: PageParams = {},
  context: RequestContext = {},
): Promise<Page<ArtifactVersion>> {
  return api.get<Page<ArtifactVersion>>(`${ARTIFACTS}/${artifactId}/versions`, {
    ...context,
    query: { page: params.page, size: params.size },
  });
}

/** Recupera uma versao especifica pelo numero sequencial do artefato (RF08). */
export function getArtifactVersion(
  artifactId: Uuid,
  versionNumber: number,
  context: RequestContext = {},
): Promise<ArtifactVersion> {
  return api.get<ArtifactVersion>(`${ARTIFACTS}/${artifactId}/versions/${versionNumber}`, context);
}

/**
 * Registra a revisao humana como versao nova (RF14).
 *
 * A origem e definida pelo servico a partir do token: o que vem desta chamada
 * e sempre `HUMANO`, e e essa distincao que sustenta a metrica de correcao da
 * saida da IA (RNF04).
 */
export function createArtifactVersion(
  artifactId: Uuid,
  payload: ArtifactVersionCreate,
  context: RequestContext = {},
): Promise<ArtifactVersion> {
  return api.post<ArtifactVersion, ArtifactVersionCreate>(
    `${ARTIFACTS}/${artifactId}/versions`,
    payload,
    context,
  );
}
