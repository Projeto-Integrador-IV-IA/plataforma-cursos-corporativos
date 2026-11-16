import { useQuery } from "@tanstack/react-query";
import { Link } from "react-router-dom";

import { PATHS, buildPath } from "@/app/paths";
import { STAGE_LABELS } from "@/features/demands/DemandListLabels";
import { isApiError } from "@/services/api";
import { listClients } from "@/services/clients";
import { getPipelineBoard } from "@/services/pipeline";
import type { PipelineCardRead } from "@/types/api";

function errorMessage(error: unknown) {
  return isApiError(error)
    ? error.message
    : "Não foi possível carregar este resumo.";
}

function formatDate(value: string) {
  return new Intl.DateTimeFormat("pt-BR", {
    day: "2-digit",
    month: "short",
  }).format(new Date(value));
}

export function HomePage() {
  const board = useQuery({
    queryKey: ["home", "pipeline"],
    queryFn: ({ signal }) => getPipelineBoard({ limit: 20 }, { signal }),
  });
  const clients = useQuery({
    queryKey: ["home", "clients"],
    queryFn: ({ signal }) => listClients({ size: 1 }, { signal }),
  });

  const recent = (board.data?.stages.flatMap((group) => group.items) ?? [])
    .sort((a, b) => Date.parse(b.updated_at) - Date.parse(a.updated_at))
    .slice(0, 5);
  const attention =
    board.data?.stages.reduce(
      (sum, group) =>
        sum + group.items.filter((item) => item.owner === null).length,
      0,
    ) ?? 0;
  const maxStage = Math.max(
    1,
    ...(board.data?.stages.map((group) => group.total) ?? [1]),
  );

  return (
    <section className="page page--wide home-page">
      <header className="home-header">
        <div>
          <p className="home-kicker">CURSOS CORPORATIVOS</p>
          <h1 className="page__title">Visão geral</h1>
          <p className="home-intro">
            Acompanhe clientes e negociações em andamento.
          </p>
        </div>
        <Link className="button home-header__action" to={PATHS.demandNew}>
          + Nova demanda
        </Link>
      </header>

      {(board.isError || clients.isError) && (
        <p className="home-error" role="alert">
          {errorMessage(board.error ?? clients.error)}
        </p>
      )}

      <div className="home-metrics">
        <Link className="home-metric" to={PATHS.clients}>
          <span>Clientes ativos</span>
          <strong>
            {clients.isPending ? "—" : (clients.data?.total ?? 0)}
          </strong>
          <small>Empresas cadastradas</small>
        </Link>
        <Link className="home-metric" to={PATHS.pipeline}>
          <span>Negociações abertas</span>
          <strong>{board.isPending ? "—" : (board.data?.total ?? 0)}</strong>
          <small>Distribuídas pelo pipeline</small>
        </Link>
        <Link
          className="home-metric home-metric--attention"
          to={PATHS.pipeline}
        >
          <span>Sem responsável</span>
          <strong>{board.isPending ? "—" : attention}</strong>
          <small>Demandas para atribuir</small>
        </Link>
      </div>

      <div className="home-panels">
        <section className="home-panel" aria-labelledby="home-pipeline-title">
          <header className="home-panel__header">
            <div>
              <p className="home-panel__eyebrow">ACOMPANHAMENTO</p>
              <h2 id="home-pipeline-title">Demandas por etapa</h2>
            </div>
            <Link to={PATHS.pipeline}>
              Abrir pipeline <span aria-hidden="true">→</span>
            </Link>
          </header>
          {board.isPending ? (
            <p className="home-state">Carregando etapas…</p>
          ) : (
            board.data?.stages.map((group) => (
              <div className="home-stage" key={group.stage}>
                <div className="home-stage__label">
                  <span>{STAGE_LABELS[group.stage]}</span>
                  <strong>{group.total}</strong>
                </div>
                <div className="home-stage__track">
                  <span
                    style={{
                      width: `${Math.max(group.total ? 7 : 0, (group.total / maxStage) * 100)}%`,
                    }}
                  />
                </div>
              </div>
            ))
          )}
        </section>

        <section
          className="home-panel home-recent"
          aria-labelledby="home-recent-title"
        >
          <header className="home-panel__header">
            <div>
              <p className="home-panel__eyebrow">CARTEIRA</p>
              <h2 id="home-recent-title">Atualizadas recentemente</h2>
            </div>
            <Link to={PATHS.demands}>
              Ver demandas <span aria-hidden="true">→</span>
            </Link>
          </header>
          {board.isPending ? (
            <p className="home-state">Carregando demandas…</p>
          ) : recent.length === 0 ? (
            <p className="home-state">
              Ainda não há demandas cadastradas.{" "}
              <Link to={PATHS.demandNew}>Criar a primeira</Link>
            </p>
          ) : (
            <ul className="home-recent__list">
              {recent.map((item: PipelineCardRead) => (
                <li key={item.id}>
                  <Link to={buildPath.demandDetail(item.id)}>
                    <span className="home-recent__title">{item.title}</span>
                    <span className="home-recent__client">
                      {item.client.name}
                    </span>
                  </Link>
                  <time dateTime={item.updated_at}>
                    {formatDate(item.updated_at)}
                  </time>
                </li>
              ))}
            </ul>
          )}
        </section>
      </div>
    </section>
  );
}
