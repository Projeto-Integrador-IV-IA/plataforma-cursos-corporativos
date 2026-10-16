/**
 * Quadro do pipeline por etapas (RF05).
 *
 * A tela e a moldura: titulo, o que o quadro mostra e o atalho para a mesma
 * carteira em lista (RF03). O quadro em si vive em
 * `features/pipeline/PipelineBoardView`, que e quem conhece o contrato de
 * `GET /api/v1/pipeline`.
 *
 * TODO(RF06): oferecer a movimentacao de etapa aqui - arrastar o cartao
 * (card #95) e avancar/retroceder com justificativa (card #96) - quando as
 * operacoes de transicao estiverem publicadas no contrato.
 */

import { Link } from 'react-router-dom';

import { PATHS } from '@/app/paths';
import { PipelineBoardView } from '@/features/pipeline/PipelineBoardView';

export function PipelinePage() {
  return (
    <section className="page page--wide">
      <header className="page__header">
        <h1 className="page__title">Pipeline</h1>
        <p className="page__requirements">
          <span className="tag">RF05</span>
        </p>
      </header>
      <p className="page__description">
        Demandas distribuidas pelas etapas, na ordem em que o pipeline as percorre.{' '}
        <Link to={PATHS.demands}>Ver a mesma carteira em lista</Link>
      </p>
      <PipelineBoardView />
    </section>
  );
}
