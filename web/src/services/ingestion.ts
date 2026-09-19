/**
 * Chamadas ao gateway para este dominio.
 *
 * Cada funcao corresponde a uma operacao declarada no contrato OpenAPI
 * (packages/contracts/openapi/). Tipos de entrada e saida vivem em `src/types`
 * e derivam do mesmo contrato (RNF02).
 *
 * Estado do contrato: `ingestion-service.yaml` ainda e esqueleto. Os caminhos
 * abaixo usam o prefixo `/ingestion` acordado em
 * docs/02-arquitetura/contratos-api.md e os campos seguem o dicionario de
 * dados; serao CONFIRMADOS quando o contrato for publicado.
 */

import { api, type RequestContext } from '@/services/api';
import type { Page, PageParams, RawInput, RawInputCreate, Uuid } from '@/types/api';

const RESOURCE = '/ingestion';

/**
 * Registra a demanda bruta em texto livre (RF09).
 *
 * O texto original e persistido antes de qualquer processamento e nunca e
 * alterado depois - e o que garante RNF05. O autor vem do token, nao do corpo.
 */
export function createRawInput(
  demandId: Uuid,
  payload: RawInputCreate,
  context: RequestContext = {},
): Promise<RawInput> {
  return api.post<RawInput, RawInputCreate>(
    `${RESOURCE}/demands/${demandId}/raw-inputs`,
    payload,
    context,
  );
}

/** Lista as entradas brutas de uma demanda, da mais recente para a mais antiga. */
export function listRawInputs(
  demandId: Uuid,
  params: PageParams = {},
  context: RequestContext = {},
): Promise<Page<RawInput>> {
  return api.get<Page<RawInput>>(`${RESOURCE}/demands/${demandId}/raw-inputs`, {
    ...context,
    query: { page: params.page, size: params.size },
  });
}

/** Busca uma entrada bruta pelo identificador. */
export function getRawInput(rawInputId: Uuid, context: RequestContext = {}): Promise<RawInput> {
  return api.get<RawInput>(`${RESOURCE}/raw-inputs/${rawInputId}`, context);
}

/**
 * Normaliza o texto bruto (RF10).
 *
 * Preenche `normalized_content` e sinaliza `truncated` quando houve corte por
 * limite de tamanho; `original_content` permanece intacto.
 */
export function normalizeRawInput(
  rawInputId: Uuid,
  context: RequestContext = {},
): Promise<RawInput> {
  return api.post<RawInput, Record<string, never>>(
    `${RESOURCE}/raw-inputs/${rawInputId}/normalize`,
    {},
    context,
  );
}
