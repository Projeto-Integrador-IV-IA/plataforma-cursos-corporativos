/**
 * Detalhe da negociacao: pipeline, historico e artefatos (RF04-RF07, RF15).
 *
 * TODO(RF04): consumir GET /api/v1/demands/{id} e as transicoes de etapa.
 */

import { useParams } from 'react-router-dom';

import { PagePlaceholder } from '@/components/PagePlaceholder';

export function DemandDetailPage() {
  const { demandId } = useParams<{ demandId: string }>();

  return (
    <PagePlaceholder
      title="Detalhe da demanda"
      requirements={['RF04', 'RF05', 'RF06', 'RF07', 'RF15']}
      description={`Pipeline, historico de etapas e artefatos da demanda ${demandId ?? ''}.`}
    />
  );
}
