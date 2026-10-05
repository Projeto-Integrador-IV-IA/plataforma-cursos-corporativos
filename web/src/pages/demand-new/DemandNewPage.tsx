/**
 * Tela de abertura de negociacao (RF02).
 *
 * Rota propria em vez de um bloco dentro da listagem: a listagem com filtros
 * (RF03) e outro card, e dividir a mesma tela entre os dois deixaria as duas
 * entregas disputando o mesmo componente.
 */

import { Link } from 'react-router-dom';

import { PATHS } from '@/app/paths';
import { DemandForm } from '@/features/demands/DemandForm';

export function DemandNewPage() {
  return (
    <section className="page">
      <header className="page__header">
        <h1 className="page__title" id="titulo-nova-demanda">
          Nova demanda
        </h1>
        <p className="page__requirements">
          <span className="tag">RF02</span>
        </p>
        <p className="page__description">
          A negociacao nasce vinculada a um cliente, na etapa de captacao. Depois de criada, a tela
          de detalhe reune fontes, etapas e artefatos.
        </p>
      </header>

      <DemandForm />

      <p className="page__description">
        <Link to={PATHS.demands}>Voltar para a lista de demandas</Link>
      </p>
    </section>
  );
}
