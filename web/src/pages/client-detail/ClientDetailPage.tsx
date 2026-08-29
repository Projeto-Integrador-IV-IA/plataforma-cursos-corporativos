/**
 * Detalhe de uma empresa cliente (RF01).
 *
 * TODO(RF01): consumir GET /api/v1/clients/{id} e a edicao dos dados.
 */

import { useParams } from 'react-router-dom';

import { PagePlaceholder } from '@/components/PagePlaceholder';

export function ClientDetailPage() {
  const { clientId } = useParams<{ clientId: string }>();

  return (
    <PagePlaceholder
      title="Detalhe do cliente"
      requirements={['RF01']}
      description={`Dados cadastrais e demandas do cliente ${clientId ?? ''}.`}
    />
  );
}
