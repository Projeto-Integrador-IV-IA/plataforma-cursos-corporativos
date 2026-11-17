import { useQuery } from '@tanstack/react-query';

import { formatarDataHora, rotuloDaEtapa } from '@/features/demands/DemandDetailLabels';
import { isApiError } from '@/services/api';
import { listStageTransitions } from '@/services/pipeline';
import type { Uuid } from '@/types/api';

const GENERIC_FAILURE = 'Nao foi possivel carregar o historico da demanda. Tente novamente.';

interface DemandStageTimelineProps {
  readonly demandId: Uuid;
}

function errorMessage(error: unknown): string {
  return isApiError(error) ? error.message : GENERIC_FAILURE;
}

export function DemandStageTimeline({ demandId }: DemandStageTimelineProps) {
  const timeline = useQuery({
    queryKey: ['demands', demandId, 'stage-timeline'],
    queryFn: ({ signal }) => listStageTransitions(demandId, { signal }),
  });

  if (timeline.isPending) {
    return (
      <p className="demand-timeline__state" aria-live="polite">
        Carregando historico…
      </p>
    );
  }

  if (timeline.isError) {
    return (
      <div className="demand-timeline__state demand-timeline__state--error" aria-live="assertive">
        <p>{errorMessage(timeline.error)}</p>
        <button type="button" className="button" onClick={() => void timeline.refetch()}>
          Tentar novamente
        </button>
      </div>
    );
  }

  if (timeline.data.items.length === 0) {
    return <p className="demand-timeline__state">Nenhuma movimentacao registrada.</p>;
  }

  return (
    <ol className="demand-timeline">
      {timeline.data.items.map((transition) => (
        <li className="demand-timeline__item" key={transition.id}>
          <p className="demand-timeline__event">
            {transition.from_stage === null
              ? `Entrada no pipeline: ${rotuloDaEtapa(transition.to_stage)}`
              : `Mudanca de etapa: ${rotuloDaEtapa(transition.from_stage)} para ${rotuloDaEtapa(
                  transition.to_stage,
                )}`}
          </p>
          <p className="demand-timeline__meta">
            Por {transition.author.name}
            {transition.reason ? ` · Justificativa: ${transition.reason}` : ''}
            {' · '}
            <time dateTime={transition.occurred_at}>
              {formatarDataHora(transition.occurred_at)}
            </time>
          </p>
        </li>
      ))}
    </ol>
  );
}
