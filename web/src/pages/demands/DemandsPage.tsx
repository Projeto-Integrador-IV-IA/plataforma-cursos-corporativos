/**
 * Lista de demandas com filtro por status, cliente e periodo (RF02, RF03).
 *
 * TODO(RF03): consumir GET /api/v1/demands com os filtros do contrato
 * (?status=, ?client_id=, ?from=, ?to=).
 */

import { PagePlaceholder } from '@/components/PagePlaceholder';

export function DemandsPage() {
  return (
    <PagePlaceholder
      title="Demandas"
      requirements={['RF02', 'RF03']}
      description="Demandas vinculadas a cliente, com filtro por status, cliente e periodo."
    />
  );
}
