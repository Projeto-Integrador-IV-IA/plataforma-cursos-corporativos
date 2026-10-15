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

import { CAMPOS_DO_CURSO, type CampoDoCurso } from '@/features/demands/StructuredCourseContent';

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
