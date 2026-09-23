/**
 * Rotulos legiveis de etapa e situacao (RF03).
 *
 * O contrato transporta os valores em caixa alta (`CAPTACAO`, `ABERTA`) porque
 * sao codigos estaveis; a tela nao os exibe crus. Os mapas ficam fora dos
 * componentes para que a tabela e o filtro escrevam o mesmo nome para o mesmo
 * valor - divergencia entre os dois confunde quem filtra.
 *
 * Sao `Record` completos de proposito: acrescentar uma etapa ou situacao ao
 * contrato sem dar nome a ela quebra a compilacao, em vez de produzir celula
 * vazia em producao.
 */

import type { DemandStatus, PipelineStage } from '@/types/api';

export const STAGE_LABELS: Record<PipelineStage, string> = {
  CAPTACAO: 'Captacao',
  ESTRUTURACAO: 'Estruturacao',
  PRODUTO: 'Produto',
  PROPOSTA: 'Proposta',
  ACOMPANHAMENTO: 'Acompanhamento',
};

export const STATUS_LABELS: Record<DemandStatus, string> = {
  ABERTA: 'Aberta',
  GANHA: 'Ganha',
  PERDIDA: 'Perdida',
  CANCELADA: 'Cancelada',
};
