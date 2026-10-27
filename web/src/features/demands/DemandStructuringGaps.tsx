/**
 * Destaque dos campos que a IA admitiu nao saber (RF15).
 *
 * E o argumento mais forte do projeto contra alucinacao: o que o modelo nao
 * encontrou na fonte aparece marcado, com o motivo, em vez de passar como
 * campo normal. Sem isso o operador aprovaria no automatico um valor que
 * ninguem confirmou.
 *
 * Os tres tipos (ausente, ambigua, contraditoria) sao distinguidos por quatro
 * canais, e nenhum deles e a cor sozinha (acessibilidade):
 *  - o nome do tipo, por escrito, dentro do destaque;
 *  - a frase do que fazer, que e diferente para cada tipo;
 *  - uma marca de forma propria, decorativa e `aria-hidden`;
 *  - a forma da borda do destaque - tracejada, pontilhada ou dupla.
 * A cor entra so como reforco: quem le em tons de cinza, com daltonismo ou em
 * papel continua distinguindo os tres.
 *
 * Lacuna de campo que esta tela nao apresenta nao e descartada: ela aparece na
 * lista de campos a confirmar, com o nome do campo como o servico o declarou.
 */

import { classesDoDestaque, sufixoDoTipo } from '@/features/demands/DemandStructuringGapStyles';
import {
  acaoDoTipoDeLacuna,
  marcaDoTipoDeLacuna,
  rotuloDoCampo,
  rotuloDoTipoDeLacuna,
} from '@/features/demands/DemandStructuringLabels';
import type { LacunaLida } from '@/features/demands/StructuredCourseContent';

interface DemandStructuringGapNoteProps {
  lacuna: LacunaLida;
}

/** Aviso de lacuna exibido junto ao campo que ela aponta. */
export function DemandStructuringGapNote({ lacuna }: DemandStructuringGapNoteProps) {
  return (
    <p className={`structuring-gap structuring-gap--${sufixoDoTipo(lacuna)}`}>
      <span className="structuring-gap__mark" aria-hidden="true">
        {marcaDoTipoDeLacuna(lacuna)}
      </span>
      <span className="structuring-gap__text">
        <strong className="structuring-gap__kind">{rotuloDoTipoDeLacuna(lacuna)}</strong> —{' '}
        {acaoDoTipoDeLacuna(lacuna)}
        {lacuna.motivo === null ? (
          <span className="structuring-gap__reason">
            O modelo nao registrou o motivo desta lacuna.
          </span>
        ) : (
          <span className="structuring-gap__reason">Motivo: {lacuna.motivo}</span>
        )}
      </span>
    </p>
  );
}

interface DemandStructuringGapListProps {
  lacunas: readonly LacunaLida[];
}

/** Lista de todos os campos que pedem confirmacao humana, em um lugar so. */
export function DemandStructuringGapList({ lacunas }: DemandStructuringGapListProps) {
  if (lacunas.length === 0) {
    return (
      <p className="demand-detail__empty">
        A estruturacao nao apontou lacuna nenhuma. Confira os campos de todo modo: a revisao humana
        e o que autoriza o uso externo.
      </p>
    );
  }

  return (
    <ul className="structuring-gaps">
      {lacunas.map((lacuna, indice) => (
        <li
          className={`structuring-gaps__item${classesDoDestaque([lacuna])}`}
          key={`${indice}-${lacuna.campo}-${lacuna.tipoDeclarado}`}
        >
          <p className="structuring-gaps__field">{rotuloDoCampo(lacuna.campo)}</p>
          <DemandStructuringGapNote lacuna={lacuna} />
        </li>
      ))}
    </ul>
  );
}
