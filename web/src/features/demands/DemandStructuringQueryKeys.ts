/**
 * Chaves de cache da revisao da estruturacao (RF19).
 *
 * Os resultados anexados a demanda ficam sob o mesmo prefixo do detalhe
 * (`DEMANDS_KEY`): quando a demanda muda, invalidar o prefixo alcanca tambem
 * a estrutura gerada, sem que esta tela precise ser lembrada caso a caso.
 */

import { DEMANDS_KEY } from '@/features/demands/DemandDetailQueryKeys';
import type { Uuid } from '@/types/api';

/** Chave dos resultados da IA anexados a uma demanda. */
export function demandArtifactsKey(demandId: Uuid) {
  return [...DEMANDS_KEY, 'artifacts', demandId] as const;
}

/**
 * Chave do estado de uma execucao de estruturacao (RF24).
 *
 * E por identificador de execucao, e nao por demanda: a mesma demanda pode ter
 * sido reenviada, e o que a tela acompanha e uma execucao especifica.
 */
export function structuringJobKey(jobId: Uuid) {
  return ['structuring', 'jobs', jobId] as const;
}
