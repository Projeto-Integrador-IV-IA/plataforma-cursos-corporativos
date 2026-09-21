/**
 * Chamadas ao gateway para este dominio.
 *
 * Cada funcao corresponde a uma operacao declarada no contrato OpenAPI
 * (packages/contracts/openapi/). Tipos de entrada e saida vivem em `src/types`
 * e derivam do mesmo contrato (RNF02).
 *
 * Estado do contrato: `createDemand`, `getDemand` e `updateDemand` ja estao
 * declaradas em `pipeline-service.yaml`, e entrada e saida espelham os schemas
 * de la. Atencao ao retorno das duas ultimas: o contrato devolve `DemandDetail`
 * - a demanda com o cliente e os artefatos aninhados -, e nao `DemandRead`,
 * como este modulo prometia enquanto a operacao nao estava publicada.
 */

import { api, type RequestContext } from '@/services/api';
import type {
  DemandCreate,
  DemandDetail,
  DemandListParams,
  DemandRead,
  DemandUpdate,
  Page,
  Uuid,
} from '@/types/api';

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

/**
 * Busca o contexto de uma demanda pelo identificador (RF02, RF04).
 *
 * A resposta e o agregado `DemandDetail`: alem dos campos da demanda, traz o
 * cliente e os artefatos com suas versoes, de proposito, para a tela de
 * detalhe nao precisar de uma segunda consulta.
 */
export function getDemand(demandId: Uuid, context: RequestContext = {}): Promise<DemandDetail> {
  return api.get<DemandDetail>(`${RESOURCE}/${demandId}`, context);
}

/**
 * Edita titulo, contexto ou responsavel da demanda (RF02).
 *
 * Altera somente os campos enviados; `description` e `owner_id` enviados como
 * `null` sao limpos. Etapa e situacao nao passam por aqui: mudam pelas
 * operacoes de pipeline (RF05, RF06), que registram a transicao no historico.
 *
 * Devolve o mesmo agregado de `getDemand`, ja atualizado - por isso a tela
 * pode escrever a resposta direto no cache em vez de recarregar.
 */
export function updateDemand(
  demandId: Uuid,
  payload: DemandUpdate,
  context: RequestContext = {},
): Promise<DemandDetail> {
  return api.patch<DemandDetail, DemandUpdate>(`${RESOURCE}/${demandId}`, payload, context);
}
