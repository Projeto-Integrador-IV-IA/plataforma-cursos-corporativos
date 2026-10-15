/**
 * Revisao da saida da IA antes de qualquer uso externo (RF19, RF14).
 *
 * A IA nunca e a palavra final: esta tela e o ponto obrigatorio de revisao
 * humana do curso estruturado.
 *
 * A pagina so resolve o identificador da rota e monta a moldura; o conteudo
 * vive em `features/demands/DemandStructuringView`, que e quem conhece o
 * artefato devolvido pelo contrato.
 *
 * TODO(#101, #102): acrescentar a edicao dos campos gerados e a decisao de
 * revisao (aprovar, rejeitar, devolver), cada uma registrando versao nova.
 */

import { Link, useParams } from 'react-router-dom';

import { buildPath, PATHS } from '@/app/paths';
import { DemandStructuringView } from '@/features/demands/DemandStructuringView';

export function DemandStructuringPage() {
  const { demandId } = useParams<{ demandId: string }>();

  return (
    <section className="page">
      <header className="page__header">
        <h1 className="page__title">Revisao da estruturacao</h1>
        <p className="page__requirements">
          <span className="tag">RF19</span>
          <span className="tag">RF15</span>
          <span className="tag">RF14</span>
        </p>
        <p className="page__description">
          A estrutura abaixo foi gerada pela IA e vale como proposta de trabalho, nunca como
          palavra final: confira cada campo contra as fontes antes de levar qualquer coisa ao
          cliente.
        </p>
      </header>

      {demandId === undefined ? (
        <p className="page__pending">Demanda nao informada no endereco.</p>
      ) : (
        <DemandStructuringView demandId={demandId} />
      )}

      <p className="page__description">
        {demandId === undefined ? (
          <Link to={PATHS.demands}>Voltar para a lista de demandas</Link>
        ) : (
          <Link to={buildPath.demandDetail(demandId)}>Voltar para o detalhe da demanda</Link>
        )}
      </p>
    </section>
  );
}
