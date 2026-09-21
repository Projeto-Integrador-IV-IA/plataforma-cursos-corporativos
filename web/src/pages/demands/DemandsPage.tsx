/**
 * Lista de demandas com filtro por status, cliente e periodo (RF02, RF03).
 *
 * A abertura de negociacao ja existe, em `/demandas/nova` (RF02). O que falta
 * aqui e a listagem em si.
 *
 * TODO(RF03): consumir GET /api/v1/demands com os filtros do contrato
 * (?status=, ?client_id=, ?stage=, ?owner_id=, ?from=, ?to=, ?limit=, ?offset=).
 */

import { Link } from 'react-router-dom';

import { PATHS } from '@/app/paths';
import { PagePlaceholder } from '@/components/PagePlaceholder';

export function DemandsPage() {
  return (
    <>
      <PagePlaceholder
        title="Demandas"
        requirements={['RF02', 'RF03']}
        description="Demandas vinculadas a cliente, com filtro por status, cliente e periodo."
      />
      <p className="page__description">
        <Link to={PATHS.demandNew}>Abrir nova demanda</Link>
      </p>
    </>
  );
}
