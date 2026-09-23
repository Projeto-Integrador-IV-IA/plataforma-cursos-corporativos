/**
 * Revisao da saida da IA antes de qualquer uso externo (RF12, RF14).
 *
 * A IA nunca e a palavra final: esta tela e o ponto obrigatorio de revisao
 * humana do curso estruturado.
 *
 * TODO(RF14): implementar a edicao do curso estruturado e o aceite explicito.
 */

import { useParams } from 'react-router-dom';

import { PagePlaceholder } from '@/components/PagePlaceholder';

export function DemandStructuringPage() {
  const { demandId } = useParams<{ demandId: string }>();

  return (
    <PagePlaceholder
      title="Estruturacao por IA"
      requirements={['RF12', 'RF14']}
      description={`Revisao e edicao humana do curso estruturado da demanda ${demandId ?? ''}.`}
    />
  );
}
