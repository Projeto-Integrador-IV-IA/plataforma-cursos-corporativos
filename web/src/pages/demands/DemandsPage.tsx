/**
 * Lista de demandas com filtro por situacao e cliente (RF02, RF03).
 *
 * A tela e a moldura: titulo, o acesso a abertura de negociacao (RF02, que ja
 * existe em `/demandas/nova`) e a listagem em si, que mora em
 * `features/demands/DemandList`.
 *
 * TODO(RF03): oferecer tambem o filtro por periodo (`?from=`, `?to=`), que o
 * contrato ja aceita.
 */

import { Link } from 'react-router-dom';

import { PATHS } from '@/app/paths';
import { DemandList } from '@/features/demands/DemandList';

export function DemandsPage() {
  return (
    <section className="page">
      <header className="page__header">
        <h1 className="page__title">Demandas</h1>
        <p className="page__requirements">
          <span className="tag">RF02</span>
          <span className="tag">RF03</span>
        </p>
      </header>
      <p className="page__description">
        Demandas vinculadas a cliente, da mais recente para a mais antiga.{' '}
        <Link to={PATHS.demandNew}>Abrir nova demanda</Link>
      </p>
      <DemandList />
    </section>
  );
}
