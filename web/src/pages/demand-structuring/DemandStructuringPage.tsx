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
import { PermissionGate } from '@/features/auth/Authorization';
import { PERMISSIONS } from '@/features/auth/permissions';
import { DemandStructuringView } from '@/features/demands/DemandStructuringView';

export function DemandStructuringPage() {
  const { demandId } = useParams<{ demandId: string }>();

  return (
    <section className="page">
      <header className="page__header">
        <h1 className="page__title">Fazer o curso com IA</h1>
        <p className="page__requirements">
          <span className="tag">Geracao</span>
          <span className="tag">Revisao humana</span>
        </p>
        <p className="page__description">
          A IA organiza os requisitos e propoe uma ementa a partir do texto captado. Depois, confira
          o resultado e as fontes antes de usar o material com o cliente.
        </p>
      </header>

      {demandId === undefined ? (
        <p className="page__pending">Demanda nao informada no endereco.</p>
      ) : (
        <DemandStructuringView demandId={demandId} />
      )}

      <p className="page__description">
        {demandId === undefined ? (
          <PermissionGate permission={PERMISSIONS.demandsRead}>
            <Link to={PATHS.demands}>Voltar para a lista de demandas</Link>
          </PermissionGate>
        ) : (
          <PermissionGate permission={PERMISSIONS.demandsRead}>
            <Link to={buildPath.demandDetail(demandId)}>Voltar para o detalhe da demanda</Link>
          </PermissionGate>
        )}
      </p>
    </section>
  );
}
