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

import { Link, useParams } from 'react-router-dom';

import { PATHS } from '@/app/paths';
import { DemandDetailView } from '@/features/demands/DemandDetailView';

export function DemandDetailPage() {
  const { demandId } = useParams<{ demandId: string }>();

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
        <DemandDetailView demandId={demandId} />
      )}

      <p className="page__description">
        <Link to={PATHS.demands}>Voltar para a lista de demandas</Link>
      </p>
    </section>
  );
}
