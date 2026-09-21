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
 * aceita somente `page` e `size` no contrato de hoje; os demais filtros
 * acompanham a tela de listagem (RF03).
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

/**
 * Busca um cliente pelo identificador (RF01).
 *
 * Identificador inexistente devolve 404 com o envelope de erro da plataforma,
 * que o cliente HTTP entrega como `ApiError` - e a tela de detalhe o trata como
 * estado de vazio, nao como falha.
 */
export function getClient(clientId: Uuid, context: RequestContext = {}): Promise<Client> {
  return api.get<Client>(`${RESOURCE}/${clientId}`, context);
}

/** Cadastra um cliente (RF01). */
export function createClient(payload: ClientCreate, context: RequestContext = {}): Promise<Client> {
  return api.post<Client, ClientCreate>(RESOURCE, payload, context);
}

/**
 * Edita os dados cadastrais de um cliente (RF01).
 *
 * Altera somente os campos enviados; campo opcional enviado como `null` e
 * limpo. Devolve o cadastro ja atualizado, por isso a tela de detalhe pode
 * escrever a resposta no cache em vez de recarregar.
 *
 * A inativacao NAO passa por aqui: o schema recusa propriedade desconhecida
 * (`additionalProperties: false`) e reserva `active` a operacao propria do
 * RF01.3 - enviar o campo nesta chamada devolveria 422.
 */
export function updateClient(
  clientId: Uuid,
  payload: ClientUpdate,
  context: RequestContext = {},
): Promise<Client> {
  return api.patch<Client, ClientUpdate>(`${RESOURCE}/${clientId}`, payload, context);
}
