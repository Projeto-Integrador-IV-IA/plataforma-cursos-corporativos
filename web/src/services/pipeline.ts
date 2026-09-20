/**
 * Chamadas ao gateway para este dominio.
 *
 * Cada funcao corresponde a uma operacao declarada no contrato OpenAPI
 * (packages/contracts/openapi/). Tipos de entrada e saida vivem em `src/types`
 * e derivam do mesmo contrato (RNF02).
 *
 * Estado do contrato: `pipeline-service.yaml` ja declara os enums de etapa e
 * situacao, mas ainda nao as rotas de transicao (RF05, RF06, RF07). Os
 * caminhos seguem a convencao de subrecurso de
 * docs/02-arquitetura/contratos-api.md (`/demands/{id}/transitions`) e serao
 * CONFIRMADOS quando o contrato for publicado.
 */

import { api, type RequestContext } from '@/services/api';
import type {
  DemandRead,
  Page,
  PageParams,
  PipelineStage,
  StageTransition,
  StageTransitionCreate,
  Uuid,
} from '@/types/api';

const RESOURCE = '/demands';

/**
 * Move a demanda para outra etapa (RF05, RF06).
 *
 * Avanco vai apenas para a etapa seguinte; retrocesso alcanca qualquer etapa
 * anterior e exige justificativa. Quem valida e o servico - a interface so
 * reporta o erro `INVALID_STAGE_TRANSITION` quando ele vem. A resposta traz a
 * demanda atualizada, entao a tela nao precisa recarregar para saber a etapa
 * corrente.
 */
export function moveDemandStage(
  demandId: Uuid,
  payload: StageTransitionCreate,
  context: RequestContext = {},
): Promise<DemandRead> {
  return api.post<DemandRead, StageTransitionCreate>(
    `${RESOURCE}/${demandId}/transitions`,
    payload,
    context,
  );
}

/** Avanca a demanda para a etapa informada. Justificativa e opcional (RF05). */
export function advanceDemandStage(
  demandId: Uuid,
  toStage: PipelineStage,
  reason?: string,
  context: RequestContext = {},
): Promise<DemandRead> {
  return moveDemandStage(demandId, { to_stage: toStage, reason: reason ?? null }, context);
}

/** Retrocede a demanda. A justificativa e obrigatoria no retrocesso (RF06). */
export function revertDemandStage(
  demandId: Uuid,
  toStage: PipelineStage,
  reason: string,
  context: RequestContext = {},
): Promise<DemandRead> {
  return moveDemandStage(demandId, { to_stage: toStage, reason }, context);
}

/**
 * Historico de etapas da demanda (RF07).
 *
 * Append-only: o historico so cresce, nunca e corrigido no lugar (RNF09).
 */
export function listStageTransitions(
  demandId: Uuid,
  params: PageParams = {},
  context: RequestContext = {},
): Promise<Page<StageTransition>> {
  return api.get<Page<StageTransition>>(`${RESOURCE}/${demandId}/transitions`, {
    ...context,
    query: { page: params.page, size: params.size },
  });
}
