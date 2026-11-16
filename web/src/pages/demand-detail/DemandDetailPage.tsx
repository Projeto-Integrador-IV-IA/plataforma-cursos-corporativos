/**
 * Detalhe da negociacao: contexto, cliente, etapa, fontes e artefatos
 * (RF02, RF04).
 *
 * A pagina so resolve o identificador da rota e monta a moldura; o conteudo
 * vive em `features/demands/DemandDetailView`, que e quem conhece o agregado
 * devolvido pelo contrato.
 *
 * TODO(RF05, RF06): acrescentar as transicoes de etapa e o historico quando as
 * operacoes de pipeline forem publicadas.
 */

import { Link, useParams } from "react-router-dom";

import { PATHS } from "@/app/paths";
import { PermissionGate } from "@/features/auth/Authorization";
import { PERMISSIONS } from "@/features/auth/permissions";
import { DemandDetailView } from "@/features/demands/DemandDetailView";

import "./demand-detail.css";

export function DemandDetailPage() {
  const { demandId } = useParams<{ demandId: string }>();

  return (
    <section className="page page--wide">
      <header className="demand-detail-page__header">
        <h1 className="page__title">Detalhe da demanda</h1>
        <PermissionGate permission={PERMISSIONS.demandsRead}>
          <Link className="demand-detail-page__back" to={PATHS.demands}>
            ← Voltar para demandas
          </Link>
        </PermissionGate>
      </header>

      {demandId === undefined ? (
        <p className="page__pending">Demanda nao informada no endereco.</p>
      ) : (
        <DemandDetailView demandId={demandId} />
      )}
    </section>
  );
}
