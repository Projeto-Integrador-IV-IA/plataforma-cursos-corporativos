/**
 * Chamadas ao gateway para este dominio.
 *
 * Cada funcao corresponde a uma operacao declarada no contrato OpenAPI
 * (packages/contracts/openapi/). Tipos de entrada e saida vivem em `src/types`
 * e derivam do mesmo contrato (RNF02).
 *
 * Estado do contrato: `pipeline-service.yaml` ainda nao declara os caminhos de
 * artefato (RF08, RF15). Os caminhos seguem as convencoes de
 * docs/02-arquitetura/contratos-api.md e os campos seguem o dicionario de
 * dados; serao CONFIRMADOS quando o contrato for publicado.
 */

import { api, type RequestContext } from '@/services/api';
import type {
  Artifact,
  ArtifactType,
  ArtifactVersion,
  ArtifactVersionCreate,
  Page,
  PageParams,
  Uuid,
} from '@/types/api';

const DEMANDS = '/demands';
const ARTIFACTS = '/artifacts';

/** Filtros da listagem de artefatos de uma demanda (RF15). */
export interface ArtifactListParams extends PageParams {
  readonly type?: ArtifactType;
}

/** Lista os artefatos de uma demanda (RF04, RF15). */
export function listArtifacts(
  demandId: Uuid,
  params: ArtifactListParams = {},
  context: RequestContext = {},
): Promise<Page<Artifact>> {
  return api.get<Page<Artifact>>(`${DEMANDS}/${demandId}/artifacts`, {
    ...context,
    query: { page: params.page, size: params.size, type: params.type },
  });
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
