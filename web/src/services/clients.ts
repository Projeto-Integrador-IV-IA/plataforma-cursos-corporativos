/**
 * Chamadas ao gateway para este dominio.
 *
 * Cada funcao corresponde a uma operacao declarada no contrato OpenAPI
 * (packages/contracts/openapi/). Tipos de entrada e saida vivem em `src/types`
 * e derivam do mesmo contrato (RNF02).
 *
 * Estado do contrato: `pipeline-service.yaml` ainda nao declara os caminhos de
 * cliente (RF01). Os caminhos abaixo seguem as convencoes de
 * docs/02-arquitetura/contratos-api.md e os campos seguem o dicionario de
 * dados; ambos serao CONFIRMADOS quando o contrato for publicado - so os nomes
 * mudam, a forma das funcoes nao.
 */

import { api, type RequestContext } from '@/services/api';
import type { Client, ClientCreate, ClientListParams, ClientUpdate, Page, Uuid } from '@/types/api';

const RESOURCE = '/clients';

/** Lista clientes com paginacao e filtro (RF01, RF03). */
export function listClients(
  params: ClientListParams = {},
  context: RequestContext = {},
): Promise<Page<Client>> {
  return api.get<Page<Client>>(RESOURCE, {
    ...context,
    query: {
      page: params.page,
      size: params.size,
      search: params.search,
      active: params.active,
    },
  });
}

/** Busca um cliente pelo identificador. */
export function getClient(clientId: Uuid, context: RequestContext = {}): Promise<Client> {
  return api.get<Client>(`${RESOURCE}/${clientId}`, context);
}

/** Cadastra um cliente (RF01). */
export function createClient(payload: ClientCreate, context: RequestContext = {}): Promise<Client> {
  return api.post<Client, ClientCreate>(RESOURCE, payload, context);
}

/** Edita um cliente. Desativacao e logica, pelo campo `active` - nada e apagado. */
export function updateClient(
  clientId: Uuid,
  payload: ClientUpdate,
  context: RequestContext = {},
): Promise<Client> {
  return api.patch<Client, ClientUpdate>(`${RESOURCE}/${clientId}`, payload, context);
}
