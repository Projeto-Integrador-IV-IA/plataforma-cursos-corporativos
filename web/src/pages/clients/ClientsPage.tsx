/**
 * Lista e cadastro de empresas clientes (RF01, RF03).
 *
 * TODO(RF01): consumir GET /api/v1/clients com paginacao e o formulario de
 * cadastro, via `src/services/clients.ts`.
 */

import { PagePlaceholder } from '@/components/PagePlaceholder';

export function ClientsPage() {
  return (
    <PagePlaceholder
      title="Clientes"
      requirements={['RF01', 'RF03']}
      description="Lista de empresas clientes, com cadastro e filtro por nome e segmento."
    />
  );
}
