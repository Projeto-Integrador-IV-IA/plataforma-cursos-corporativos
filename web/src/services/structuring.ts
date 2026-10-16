/**
 * Chamadas ao gateway para este dominio.
 *
 * Cada funcao corresponde a uma operacao declarada no contrato OpenAPI
 * (packages/contracts/openapi/). Tipos de entrada e saida vivem em `src/types`
 * e derivam do mesmo contrato (RNF02).
 *
 * Estado do contrato: `POST /api/v1/structuring/jobs` e
 * `GET /api/v1/structuring/jobs/{job_id}` estao declaradas em
 * `ai-structuring-service.yaml`, e entrada e saida espelham os schemas de la.
 * O gateway ainda declara so os caminhos de autenticacao, entao a interface
 * chega a estruturacao pelo mesmo prefixo das demais chamadas - e o que vale
 * para `/demands` e `/clients` vale aqui.
 *
 * Por que o caminho assincrono e nao `POST /api/v1/structuring`: a chamada ao
 * modelo leva dezenas de segundos, e prender a tela nelas faria o operador
 * concluir que travou e clicar de novo (RF17, RNF06). O aceite devolve o
 * identificador, e o estado se consulta por ele.
 */

import { api, type RequestContext, TIMEOUTS } from '@/services/api';
import type {
  StructuringJobAccepted,
  StructuringJobRead,
  StructuringRequest,
  Uuid,
} from '@/types/api';

const RESOURCE = '/structuring/jobs';

/**
 * Aceita a estruturacao e devolve o identificador da execucao (RF17).
 *
 * Responde 202 sem esperar o modelo: o recurso devolvido e a execucao, nao o
 * curso, que ainda nao existe. O timeout e o da IA (RNF06) porque e o
 * ai-structuring-service quem atende, ainda que o aceite seja rapido.
 */
export function submitStructuringJob(
  payload: StructuringRequest,
  context: RequestContext = {},
): Promise<StructuringJobAccepted> {
  return api.post<StructuringJobAccepted, StructuringRequest>(RESOURCE, payload, {
    timeoutMs: TIMEOUTS.ai,
    ...context,
  });
}

/**
 * Consulta o estado de uma execucao pelo identificador (RF24).
 *
 * Leitura rapida, com o timeout padrao: quem espera aqui e a tela do operador,
 * nao o modelo. Enquanto a execucao nao concluiu, `result` vem nulo.
 */
export function getStructuringJob(
  jobId: Uuid,
  context: RequestContext = {},
): Promise<StructuringJobRead> {
  return api.get<StructuringJobRead>(`${RESOURCE}/${jobId}`, context);
}
