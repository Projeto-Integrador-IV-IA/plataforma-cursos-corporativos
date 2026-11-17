/**
 * Quadro do pipeline por etapas (RF05).
 *
 * A tela e a moldura: titulo, o que o quadro mostra e o atalho para a mesma
 * carteira em lista (RF03). O quadro em si vive em
 * `features/pipeline/PipelineBoardView`, que e quem conhece o contrato de
 * `GET /api/v1/pipeline`.
 *
 * Movimentacao de etapa (card #95/#96, RF06/RF07) ja esta disponivel: ver
 * arrastar-e-soltar em `PipelineBoardView`.
 */

import { Link } from "react-router-dom";

import { PATHS } from "@/app/paths";
import { PermissionGate } from "@/features/auth/Authorization";
import { PERMISSIONS } from "@/features/auth/permissions";
import { PipelineBoardView } from "@/features/pipeline/PipelineBoardView";

import "./pipeline.css";

export function PipelinePage() {
  return (
    <section className="page page--wide">
      <header className="pipeline-page__header">
        <div>
          <h1 className="page__title">Pipeline</h1>
          <p className="page__description">
            Acompanhe cada negociação pelas etapas do processo.
          </p>
        </div>
        <div className="pipeline-page__actions">
          <PermissionGate permission={PERMISSIONS.demandsRead}>
            <Link className="button button--secondary" to={PATHS.demands}>
              Ver em lista
            </Link>
          </PermissionGate>
          <PermissionGate permission={PERMISSIONS.demandsManage}>
            <Link className="button" to={PATHS.demandNew}>
              <span aria-hidden="true">+</span> Nova demanda
            </Link>
          </PermissionGate>
        </div>
      </header>
      <PipelineBoardView />
    </section>
  );
}
