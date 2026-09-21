/**
 * Chamadas ao gateway para este dominio.
 *
 * Cada funcao corresponde a uma operacao declarada no contrato OpenAPI
 * (packages/contracts/openapi/). Tipos de entrada e saida vivem em `src/types`
 * e derivam do mesmo contrato (RNF02).
 *
 * Estado do contrato: `createDemand` corresponde a `POST /api/v1/demands`, ja
 * declarada em `pipeline-service.yaml` - entrada e saida espelham
 * `DemandCreate` e `DemandRead`. As demais operacoes (RF03, RF04) seguem as
 * convencoes de docs/02-arquitetura/contratos-api.md e serao CONFIRMADAS
 * quando o contrato for publicado.
 */

import { api, type RequestContext } from '@/services/api';
import type { DemandCreate, DemandListParams, DemandRead, DemandUpdate, Page, Uuid } from '@/types/api';

const RESOURCE = '/demands';

/**
 * Cria uma demanda vinculada a um cliente (RF02).
 *
 * Situacao (`ABERTA`) e etapa inicial (`CAPTACAO`) sao definidas pelo servico:
 * o corpo nao as envia.
 */
export function createDemand(
  payload: DemandCreate,
  context: RequestContext = {},
): Promise<DemandRead> {
  return api.post<DemandRead, DemandCreate>(RESOURCE, payload, context);
}

/**
 * Lista demandas filtrando por situacao, cliente, etapa, responsavel e periodo
 * (RF03).
 *
 * A paginacao vai em `limit`/`offset`, como o contrato declara - a resposta e
 * que volta em `page`/`size`. Enquanto a operacao nao estava publicada, este
 * modulo enviava `page`/`size` tambem na entrada, e o servidor ignorava.
 */
export function listDemands(
  params: DemandListParams = {},
  context: RequestContext = {},
): Promise<Page<DemandRead>> {
  return api.get<Page<DemandRead>>(RESOURCE, {
    ...context,
    query: {
      limit: params.limit,
      offset: params.offset,
      status: params.status,
      client_id: params.client_id,
      stage: params.stage,
      owner_id: params.owner_id,
      from: params.from,
      to: params.to,
    },
  });
}

/** Busca uma demanda pelo identificador (RF04). */
export function getDemand(demandId: Uuid, context: RequestContext = {}): Promise<DemandRead> {
  return api.get<DemandRead>(`${RESOURCE}/${demandId}`, context);
}

/**
 * Edita titulo, contexto ou responsavel da demanda.
 *
 * Etapa e situacao nao passam por aqui: mudam pelas operacoes de pipeline
 * (RF05, RF06), que registram a transicao no historico.
 */
export function updateDemand(
  demandId: Uuid,
  payload: DemandUpdate,
  context: RequestContext = {},
): Promise<DemandRead> {
  return api.patch<DemandRead, DemandUpdate>(`${RESOURCE}/${demandId}`, payload, context);
}
