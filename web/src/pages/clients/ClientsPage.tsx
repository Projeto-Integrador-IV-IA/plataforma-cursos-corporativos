/**
 * Lista de empresas clientes (RF01, RF03).
 *
 * O cadastro ja existe, em `/clientes/novo` (RF01). O que falta aqui e a
 * listagem em si.
 *
 * TODO(RF03): consumir GET /api/v1/clients com paginacao, via
 * `src/services/clients.ts`.
 */

import { Link } from 'react-router-dom';

import { PATHS } from '@/app/paths';
import { PagePlaceholder } from '@/components/PagePlaceholder';

export function ClientsPage() {
  return (
    <>
      <PagePlaceholder
        title="Clientes"
        requirements={['RF01', 'RF03']}
        description="Lista de empresas clientes, com cadastro e filtro por nome e segmento."
      />
      <p className="page__description">
        <Link to={PATHS.clientNew}>Cadastrar cliente</Link>
      </p>
    </>
  );
}
