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
