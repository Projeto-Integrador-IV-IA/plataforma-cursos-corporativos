/**
 * Traducoes e formatos usados pela tela de detalhe da demanda (RF02).
 *
 * O contrato transporta codigos (`CAPTACAO`, `ABERTA`, `REQUISITOS_EXTRAIDOS`)
 * e a tela mostra o nome que o operador usa na conversa com o cliente. A
 * traducao fica em um lugar so para que etapa, situacao e tipo de artefato
 * aparecam iguais em todas as telas que vierem depois.
 *
 * Nenhum mapa e exaustivo por decisao: `type` e `origin` de artefato sao
 * declarados como string aberta no contrato, entao um codigo desconhecido
 * precisa aparecer como veio, em vez de sumir da tela.
 */

import type { DemandStatus, IsoDateTime, PipelineStage } from '@/types/api';

const ETAPAS: Readonly<Record<PipelineStage, string>> = {
  CAPTACAO: 'Captacao',
  ESTRUTURACAO: 'Estruturacao',
  PRODUTO: 'Produto',
  PROPOSTA: 'Proposta',
  ACOMPANHAMENTO: 'Acompanhamento',
};

const SITUACOES: Readonly<Record<DemandStatus, string>> = {
  ABERTA: 'Aberta',
  GANHA: 'Ganha',
  PERDIDA: 'Perdida',
  CANCELADA: 'Cancelada',
};

const TIPOS_DE_ARTEFATO: Readonly<Record<string, string>> = {
  DEMANDA_BRUTA: 'Demanda bruta',
  REQUISITOS_EXTRAIDOS: 'Requisitos extraidos',
  EMENTA: 'Ementa',
  PROPOSTA: 'Proposta',
  OUTRO: 'Outro',
};

const ORIGENS_DE_VERSAO: Readonly<Record<string, string>> = {
  IA: 'gerada pela IA',
  HUMANO: 'revisada por pessoa',
};

/** Texto exibido no lugar de um campo opcional que veio vazio. */
export const SEM_INFORMACAO = 'Nao informado';

export function rotuloDaEtapa(stage: PipelineStage): string {
  return ETAPAS[stage];
}

export function rotuloDaSituacao(status: DemandStatus): string {
  return SITUACOES[status];
}

export function rotuloDoTipoDeArtefato(type: string): string {
  return TIPOS_DE_ARTEFATO[type] ?? type;
}

export function rotuloDaOrigem(origin: string): string {
  return ORIGENS_DE_VERSAO[origin] ?? origin;
}

/**
 * Data e hora no formato brasileiro.
 *
 * O valor invalido nao quebra a tela nem vira `Invalid Date` no meio do texto:
 * volta como veio, e quem le decide o que fazer com ele.
 */
export function formatarDataHora(valor: IsoDateTime): string {
  const data = new Date(valor);

  if (Number.isNaN(data.getTime())) {
    return valor;
  }

  return new Intl.DateTimeFormat('pt-BR', {
    dateStyle: 'short',
    timeStyle: 'short',
  }).format(data);
}

/** Campo opcional de texto: devolve o valor ou o aviso de ausencia. */
export function ouSemInformacao(valor: string | null): string {
  return valor === null || valor.trim() === '' ? SEM_INFORMACAO : valor;
}
