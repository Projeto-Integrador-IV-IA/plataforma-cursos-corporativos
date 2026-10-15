/**
 * Uma coluna do quadro do pipeline (RF05).
 *
 * A coluna e uma regiao com nome (`section` + `aria-labelledby`): quem navega
 * por teclado ou leitor de tela salta de etapa em etapa, em vez de atravessar
 * uma lista unica de cartoes sem saber onde uma etapa termina e a outra
 * comeca.
 *
 * Coluna vazia nao desaparece nem fica em branco. O quadro tem cinco colunas
 * fixas - e o servico as devolve todas, inclusive as vazias -, entao a etapa
 * sem demanda se apresenta com uma area tracejada e uma frase propria. Sumir
 * com ela faria a leitura do andamento mentir: "nenhuma demanda em Proposta" e
 * informacao, nao ausencia de informacao.
 *
 * O numero no cabecalho e o total da etapa, nao o de cartoes desenhados; o
 * porque esta em `PipelineBoardLabels`.
 *
 * TODO(RF05, card #94): a demanda aparece aqui como link para o detalhe. O
 * cartao com cliente, responsavel, situacao e sinal de atencao e o card
 * seguinte e entra no lugar deste link.
 */

import { useId } from 'react';
import { Link } from 'react-router-dom';

import { buildPath } from '@/app/paths';
import { STAGE_LABELS } from '@/features/demands/DemandListLabels';
import { stageCount } from '@/features/pipeline/PipelineBoardLabels';
import type { PipelineStageGroup } from '@/types/api';

interface PipelineStageColumnProps {
  readonly group: PipelineStageGroup;
}

export function PipelineStageColumn({ group }: PipelineStageColumnProps) {
  const titleId = useId();

  return (
    <li className="pipeline-board__column">
      <section className="pipeline-column" aria-labelledby={titleId}>
        <h2 className="pipeline-column__title" id={titleId}>
          {STAGE_LABELS[group.stage]}
        </h2>
        <p className="pipeline-column__count">{stageCount(group.items.length, group.total)}</p>

        {group.items.length === 0 ? (
          <p className="pipeline-column__empty">Nenhuma demanda nesta etapa.</p>
        ) : (
          <ol className="pipeline-column__cards">
            {group.items.map((card) => (
              <li key={card.id}>
                <Link to={buildPath.demandDetail(card.id)}>{card.title}</Link>
              </li>
            ))}
          </ol>
        )}
      </section>
    </li>
  );
}
