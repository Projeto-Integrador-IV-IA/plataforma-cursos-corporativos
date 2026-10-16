/**
 * Como o destaque de lacuna muda de forma conforme o tipo (RF15).
 *
 * Vive fora do componente de proposito: e aqui que mora a decisao de que o
 * tipo da lacuna vira *forma* - borda tracejada, pontilhada ou dupla, pelas
 * classes `structuring-gap-host--*` de `styles/global.css` - e nao cor apenas.
 * Com a regra em um lugar so, o campo lido e a lista de campos a confirmar
 * nunca se contradizem sobre o mesmo apontamento.
 */

import type { LacunaLida } from '@/features/demands/StructuredCourseContent';

/**
 * Ordem de gravidade usada quando um campo acumula mais de uma lacuna: a forma
 * do destaque segue a mais grave, e as demais continuam listadas abaixo dela.
 */
const GRAVIDADE: readonly string[] = ['ausente', 'ambigua', 'contraditoria'];

/** Sufixo de classe do tipo. Tipo fora do contrato cai em `desconhecida`. */
export function sufixoDoTipo(lacuna: LacunaLida): string {
  return lacuna.tipo ?? 'desconhecida';
}

/** Lacunas apontadas para um campo, na ordem em que o servico as devolveu. */
export function lacunasDoCampo(
  lacunas: readonly LacunaLida[],
  campo: string,
): readonly LacunaLida[] {
  return lacunas.filter((lacuna) => lacuna.campo === campo);
}

/**
 * Classes do contorno de um campo com lacuna.
 *
 * Devolve string vazia quando nao ha lacuna: campo sem apontamento nao ganha
 * destaque nenhum, senao o destaque deixaria de destacar.
 */
export function classesDoDestaque(lacunas: readonly LacunaLida[]): string {
  const maisGrave = lacunas.reduce<LacunaLida | undefined>((escolhida, candidata) => {
    if (escolhida === undefined) {
      return candidata;
    }

    return GRAVIDADE.indexOf(sufixoDoTipo(candidata)) > GRAVIDADE.indexOf(sufixoDoTipo(escolhida))
      ? candidata
      : escolhida;
  }, undefined);

  if (maisGrave === undefined) {
    return '';
  }

  return ` structuring-gap-host structuring-gap-host--${sufixoDoTipo(maisGrave)}`;
}
