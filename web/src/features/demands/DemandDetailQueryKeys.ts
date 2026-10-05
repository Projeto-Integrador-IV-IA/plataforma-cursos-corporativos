/**
 * Chaves de cache do detalhe da demanda (RF02).
 *
 * Ficam fora dos componentes porque a tela le por uma chave e o formulario de
 * edicao escreve pela mesma: literal repetido em dois arquivos vira cache
 * desencontrado no dia em que um dos dois mudar.
 */

import type { Uuid } from '@/types/api';

/** Prefixo de tudo que e demanda. Invalidar por aqui alcanca lista e detalhe. */
export const DEMANDS_KEY = ['demands'] as const;

/** Chave do agregado de uma demanda especifica. */
export function demandDetailKey(demandId: Uuid) {
  return [...DEMANDS_KEY, 'detail', demandId] as const;
}
