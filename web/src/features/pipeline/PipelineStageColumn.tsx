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
 * A coluna nao sabe o que vai dentro do cartao: quem desenha a demanda e
 * `PipelineCard`. Aqui so fica a lista ordenada que a sustenta, para a ordem
 * dos cartoes dentro da etapa ser a que o servico devolveu.
 */

import { useId } from 'react';

import { STAGE_LABELS } from '@/features/demands/DemandListLabels';
import { stageCount } from '@/features/pipeline/PipelineBoardLabels';
import { PipelineCard } from '@/features/pipeline/PipelineCard';
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
                <PipelineCard card={card} />
              </li>
            ))}
          </ol>
        )}
      </section>
    </li>
  );
}
