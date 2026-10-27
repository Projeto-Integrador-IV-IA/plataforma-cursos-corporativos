/**
 * Traducoes e formatos da revisao da estruturacao (RF19).
 *
 * O contrato transporta nomes de campo (`publico_alvo`) e codigos de canal
 * (`EMAIL`); a tela mostra o nome que o operador usa na conversa com o
 * cliente. A traducao fica em um lugar so para que a revisao e as telas que
 * vierem depois nomeiem o mesmo campo do mesmo modo.
 *
 * Nenhum mapa e exaustivo por decisao: codigo desconhecido aparece como veio,
 * em vez de sumir da tela - numa revisao que existe para conferir a saida da
 * IA, dado escondido e pior que dado estranho.
 */

import {
  CAMPOS_DO_CURSO,
  type CampoDoCurso,
  type LacunaLida,
} from '@/features/demands/StructuredCourseContent';
import type { GapKind, JobStatus } from '@/types/api';

const CAMPOS: Readonly<Record<CampoDoCurso, string>> = {
  tema: 'Tema',
  nicho: 'Nicho',
  publico_alvo: 'Publico-alvo',
  numero_participantes: 'Numero de participantes',
  carga_horaria: 'Carga horaria',
  formato: 'Formato',
  objetivos_aprendizagem: 'Objetivos de aprendizagem',
  ementa: 'Ementa',
};

const FORMATOS: Readonly<Record<string, string>> = {
  presencial: 'Presencial',
  online: 'Online',
  hibrido: 'Hibrido',
};

const FONTES: Readonly<Record<string, string>> = {
  EMAIL: 'E-mail',
  TRANSCRICAO: 'Transcricao',
  MENSAGENS: 'Mensagens',
  ANOTACAO: 'Anotacao',
  OUTRO: 'Outro',
};

/** Nome exibido de um campo do curso. Campo fora do contrato sai como veio. */
export function rotuloDoCampo(campo: string): string {
  const conhecido = CAMPOS_DO_CURSO.find((nome) => nome === campo);

  return conhecido === undefined ? campo : CAMPOS[conhecido];
}

/** Formato de realizacao do treinamento, por extenso. */
export function rotuloDoFormato(formato: string): string {
  return FORMATOS[formato] ?? formato;
}

/** Canal de origem da fonte captada, por extenso. */
export function rotuloDaFonte(source: string): string {
  return FONTES[source] ?? source;
}

/** Carga horaria com a unidade, para "16" nunca ser lido como outra coisa. */
export function formatarCargaHoraria(horas: number): string {
  return horas === 1 ? '1 hora' : `${horas} horas`;
}

/** Numero de participantes com a unidade. */
export function formatarParticipantes(pessoas: number): string {
  return pessoas === 1 ? '1 participante' : `${pessoas} participantes`;
}

// ---------------------------------------------------------------------------
// Lacunas (RF15)
// ---------------------------------------------------------------------------

/**
 * Nome do tipo da lacuna.
 *
 * O nome vai por escrito, e nao so em cor ou em icone: e o unico canal que
 * chega igual a quem le a tela, a quem usa leitor de tela e a quem imprime o
 * PDF da revisao em preto e branco.
 */
const TIPOS_DE_LACUNA: Readonly<Record<GapKind, string>> = {
  ausente: 'Ausente',
  ambigua: 'Ambigua',
  contraditoria: 'Contraditoria',
};

/**
 * Marca de cada tipo, usada junto ao nome e nunca sozinha.
 *
 * Tres formas diferentes de proposito - circulo vazio para o que nao existe
 * no texto, interrogacao para o que admite mais de uma leitura, desigualdade
 * para o que se contradiz. Sao `aria-hidden` no componente: quem usa leitor
 * de tela recebe o nome do tipo, nao o desenho.
 */
const MARCAS_DE_LACUNA: Readonly<Record<GapKind, string>> = {
  ausente: '○',
  ambigua: '?',
  contraditoria: '≠',
};

/**
 * O que fazer com cada tipo de lacuna.
 *
 * E a razao de a tela distinguir os tres: cada um pede uma conversa diferente
 * com o cliente. Isto e texto de interface, nao regra - quem classifica a
 * lacuna e o servico (RNF03).
 */
const ACOES_DE_LACUNA: Readonly<Record<GapKind, string>> = {
  ausente: 'a fonte nao traz esta informacao: pergunte ao cliente.',
  ambigua: 'a fonte admite mais de uma leitura: esclareca com o cliente.',
  contraditoria: 'a fonte se contradiz neste ponto: confronte os trechos com o cliente.',
};

// ---------------------------------------------------------------------------
// Estado da execucao (RF24)
// ---------------------------------------------------------------------------

/** Nome do estado da execucao, no vocabulario do operador. */
const ESTADOS: Readonly<Record<JobStatus, string>> = {
  PENDENTE: 'Na fila',
  PROCESSANDO: 'Processando',
  CONCLUIDA: 'Concluida',
  ERRO: 'Falhou',
};

/**
 * Marca de cada estado, usada junto ao nome e nunca sozinha.
 *
 * Como nas lacunas, a distincao nao pode depender de cor: o nome do estado vai
 * por escrito e a marca e `aria-hidden` no componente.
 */
const MARCAS_DE_ESTADO: Readonly<Record<JobStatus, string>> = {
  PENDENTE: '…',
  PROCESSANDO: '◐',
  CONCLUIDA: '✓',
  ERRO: '!',
};

/** O que cada estado significa para quem espera a estrutura. */
const EXPLICACOES_DE_ESTADO: Readonly<Record<JobStatus, string>> = {
  PENDENTE: 'o pedido foi aceito e aguarda a vez na fila.',
  PROCESSANDO: 'o modelo esta trabalhando; pode levar dezenas de segundos.',
  CONCLUIDA: 'a execucao terminou e o resultado ja pode ser revisado.',
  ERRO: 'a execucao terminou sem resultado. A demanda captada continua intacta.',
};

export function rotuloDoEstado(status: JobStatus): string {
  return ESTADOS[status];
}

export function marcaDoEstado(status: JobStatus): string {
  return MARCAS_DE_ESTADO[status];
}

export function explicacaoDoEstado(status: JobStatus): string {
  return EXPLICACOES_DE_ESTADO[status];
}

/** Duracao de ponta a ponta da execucao, em segundos (RNF06). */
export function formatarDuracao(milissegundos: number): string {
  const segundos = milissegundos / 1000;

  return `${segundos.toFixed(1).replace('.', ',')} s`;
}

/** Nome do tipo da lacuna; tipo fora do contrato sai como o servico o declarou. */
export function rotuloDoTipoDeLacuna(lacuna: LacunaLida): string {
  if (lacuna.tipo === null) {
    return lacuna.tipoDeclarado === '' ? 'Sem tipo declarado' : lacuna.tipoDeclarado;
  }

  return TIPOS_DE_LACUNA[lacuna.tipo];
}

/** Marca do tipo da lacuna. Tipo desconhecido usa a marca neutra. */
export function marcaDoTipoDeLacuna(lacuna: LacunaLida): string {
  return lacuna.tipo === null ? '!' : MARCAS_DE_LACUNA[lacuna.tipo];
}

/** O que a lacuna pede do operador. */
export function acaoDoTipoDeLacuna(lacuna: LacunaLida): string {
  return lacuna.tipo === null
    ? 'o servico apontou uma lacuna que esta tela nao sabe classificar: confirme com o cliente.'
    : ACOES_DE_LACUNA[lacuna.tipo];
}
