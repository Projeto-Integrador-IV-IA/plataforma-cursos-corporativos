/**
 * Entrada de demanda bruta em texto livre (RF09).
 *
 * A demanda bruta e persistida antes de qualquer chamada ao LLM (RNF05), entao
 * esta tela confirma a gravacao antes de disparar a estruturacao.
 *
 * TODO(RF09): implementar o formulario e o envio ao ingestion-service.
 */

import { useParams } from 'react-router-dom';

import { PagePlaceholder } from '@/components/PagePlaceholder';

export function DemandIngestionPage() {
  const { demandId } = useParams<{ demandId: string }>();

  return (
    <PagePlaceholder
      title="Ingestao da demanda"
      requirements={['RF09', 'RNF05']}
      description={`Registro do texto livre recebido do cliente para a demanda ${demandId ?? ''}.`}
    />
  );
}
