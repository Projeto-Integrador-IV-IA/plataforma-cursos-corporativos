import { useQuery } from '@tanstack/react-query';
import { Link } from 'react-router-dom';

import { buildPath } from '@/app/paths';
import { formatarDataHora, rotuloDaEtapa } from '@/features/demands/DemandDetailLabels';
import { isApiError } from '@/services/api';
import { listStageTransitions } from '@/services/pipeline';
import type { PipelineCardRead, StageTransition } from '@/types/api';

const RECENT_UPDATES_LIMIT = 5;
const GENERIC_FAILURE = 'Nao foi possivel carregar as atualizacoes recentes. Tente novamente.';

interface PipelineUpdate {
  readonly transition: StageTransition;
  readonly demand: PipelineCardRead;
}

interface PipelineRecentUpdatesProps {
  readonly demands: readonly PipelineCardRead[];
}

function errorMessage(error: unknown): string {
  return isApiError(error) ? error.message : GENERIC_FAILURE;
}

function transitionTimestamp(update: PipelineUpdate): number {
  return new Date(update.transition.occurred_at).getTime();
}

export function PipelineRecentUpdates({ demands }: PipelineRecentUpdatesProps) {
  const activity = useQuery({
    queryKey: ['pipeline', 'recent-updates', demands.map(({ id }) => id)],
    queryFn: async ({ signal }) => {
      if (demands.length === 0) {
        return [];
      }

      const timelines = await Promise.all(
        demands.map(async (demand) => ({
          demand,
          timeline: await listStageTransitions(demand.id, { signal }),
        })),
      );

      return timelines
        .flatMap(({ demand, timeline }) =>
          timeline.items.map((transition) => ({ transition, demand })),
        )
        .sort((left, right) => transitionTimestamp(right) - transitionTimestamp(left))
        .slice(0, RECENT_UPDATES_LIMIT);
    },
  });

  return (
    <section className="pipeline-updates" aria-labelledby="pipeline-updates-title">
      <header className="pipeline-updates__header">
        <h2 className="pipeline-updates__title" id="pipeline-updates-title">
          Atualizacoes recentes
        </h2>
        <p className="pipeline-updates__description">
          Ultimas movimentacoes das demandas do quadro, registradas na trilha de auditoria. Abra
          uma demanda para consultar o historico completo.
        </p>
      </header>

      {activity.isPending ? (
        <p className="pipeline-updates__state" aria-live="polite">
          Carregando atualizacoes…
        </p>
      ) : null}

      {activity.isError ? (
        <div
          className="pipeline-updates__state pipeline-updates__state--error"
          aria-live="assertive"
        >
          <p>{errorMessage(activity.error)}</p>
          <button type="button" className="button" onClick={() => void activity.refetch()}>
            Tentar novamente
          </button>
        </div>
      ) : null}

      {activity.isSuccess && activity.data.length === 0 ? (
        <p className="pipeline-updates__state">Nenhuma movimentacao registrada ate agora.</p>
      ) : null}

      {activity.isSuccess && activity.data.length > 0 ? (
        <ol className="pipeline-updates__list" aria-label="Atualizacoes recentes">
          {activity.data.map(({ transition, demand }) => (
            <li className="pipeline-updates__item" key={transition.id}>
              <Link
                className="pipeline-updates__demand"
                to={buildPath.demandDetail(demand.id)}
                aria-label={`Abrir ${demand.title} e consultar o historico completo`}
              >
                {demand.title}
              </Link>
              <p className="pipeline-updates__event">
                {transition.from_stage === null
                  ? `Entrada no pipeline: ${rotuloDaEtapa(transition.to_stage)}`
                  : `Mudanca de etapa: ${rotuloDaEtapa(transition.from_stage)} para ${rotuloDaEtapa(
                      transition.to_stage,
                    )}`}
              </p>
              <p className="pipeline-updates__meta">
                Por {transition.author.name} ·{' '}
                <time dateTime={transition.occurred_at}>
                  {formatarDataHora(transition.occurred_at)}
                </time>
              </p>
            </li>
          ))}
        </ol>
      ) : null}
    </section>
  );
}
