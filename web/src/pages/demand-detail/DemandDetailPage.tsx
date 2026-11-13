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

import { Link, useLocation, useParams, useSearchParams } from 'react-router-dom';

import { buildPath, PATHS, QUERY_PARAMS } from '@/app/paths';
import { DemandDetailView } from '@/features/demands/DemandDetailView';

interface ReviewLocation {
  readonly pathname: string;
  readonly search: string;
  readonly hash: string;
}

function isRecord(value: unknown): value is Record<string, unknown> {
  return typeof value === 'object' && value !== null;
}

function getReviewReturnLocation(state: unknown, demandId: string): ReviewLocation {
  const fallback = {
    pathname: buildPath.demandStructuring(demandId),
    search: '',
    hash: '',
  };
  if (!isRecord(state) || !isRecord(state.returnTo)) return fallback;

  const candidate = state.returnTo;
  if (
    candidate.pathname !== fallback.pathname ||
    typeof candidate.search !== 'string' ||
    typeof candidate.hash !== 'string'
  ) {
    return fallback;
  }

  return {
    pathname: fallback.pathname,
    search: candidate.search,
    hash: candidate.hash,
  };
}

export function DemandDetailPage() {
  const { demandId } = useParams<{ demandId: string }>();
  const location = useLocation();
  const [searchParams] = useSearchParams();

  return (
    <section className="page">
      <header className="page__header">
        <h1 className="page__title">Detalhe da demanda</h1>
        <p className="page__requirements">
          <span className="tag">RF02</span>
          <span className="tag">RF04</span>
        </p>
      </header>

      {demandId === undefined ? (
        <p className="page__pending">Demanda nao informada no endereco.</p>
      ) : (
        <DemandDetailView
          demandId={demandId}
          selectedSourceId={searchParams.get(QUERY_PARAMS.sourceId)}
          selectedSegmentId={searchParams.get(QUERY_PARAMS.sourceSegmentId)}
          returnTo={getReviewReturnLocation(location.state, demandId)}
        />
      )}

      <p className="page__description">
        <Link to={PATHS.demands}>Voltar para a lista de demandas</Link>
      </p>
    </section>
  );
}
