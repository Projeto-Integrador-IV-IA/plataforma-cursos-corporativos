/**
 * Chaves de cache da tela de detalhe do cliente (RF01; RF01.2 no Documento
 * Consolidado v1.0).
 *
 * Ficam fora dos componentes porque a tela le por uma chave e o formulario de
 * edicao escreve pela mesma: literal repetido em dois arquivos vira cache
 * desencontrado no dia em que um dos dois mudar.
 */

import type { Uuid } from '@/types/api';

/** Prefixo de tudo que e cliente. Invalidar por aqui alcanca lista e detalhe. */
export const CLIENTS_KEY = ['clients'] as const;

/** Chave do cadastro de um cliente especifico. */
export function clientDetailKey(clientId: Uuid) {
  return [...CLIENTS_KEY, 'detail', clientId] as const;
}

/**
 * Chave das demandas exibidas no detalhe do cliente.
 *
 * Comeca por `demands` de proposito: quem cria ou edita demanda invalida esse
 * prefixo, e a lista desta tela acompanha sem precisar conhecer o cliente.
 */
export function clientDemandsKey(clientId: Uuid) {
  return ['demands', 'by-client', clientId] as const;
}
