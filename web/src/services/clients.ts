/**
 * Chamadas ao gateway para este dominio.
 *
 * Cada funcao corresponde a uma operacao declarada no contrato OpenAPI
 * (packages/contracts/openapi/). Tipos de entrada e saida vivem em `src/types`
 * e derivam do mesmo contrato (RNF02).
 *
 * Estado do contrato: `pipeline-service.yaml` ja declara `POST`, `GET`,
 * `GET /{id}` e `PATCH` de cliente (RF01), e os tipos abaixo espelham
 * `ClientCreate`, `ClientRead`, `ClientPage` e `ClientUpdate`. A listagem
 * aceita somente `page` e `size`, e e so isso que `listClients` envia: filtro
 * que o servico ignora nao e filtro, e ruido que faz a tela prometer uma busca
 * inexistente (RF03).
 */

import { api, type RequestContext } from '@/services/api';
import type { Client, ClientCreate, ClientListParams, ClientUpdate, Page, Uuid } from '@/types/api';

const RESOURCE = '/clients';

/**
 * Lista clientes com a paginacao do contrato (RF01, RF03).
 *
 * `page` comeca em 1 e `size` vai ate 100; omitidos, o servico usa 1 e 20. A
 * ordenacao e fixa no servidor (`created_at DESC, id ASC`) e nao e
 * parametrizavel - quem lista nao escolhe a ordem, so o recorte.
 */
export function listClients(
  params: ClientListParams = {},
  context: RequestContext = {},
): Promise<Page<Client>> {
  return api.get<Page<Client>>(RESOURCE, {
    ...context,
    query: {
      page: params.page,
      size: params.size,
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
