/**
 * Detalhe de uma empresa cliente (RF01; RF01.2 no Documento Consolidado v1.0).
 *
 * A pagina so resolve o identificador da rota e monta a moldura; o conteudo
 * vive em `features/clients/ClientDetailView`, que e quem conhece o cadastro
 * devolvido pelo contrato.
 *
 * O identificador aparece no cabecalho de proposito: e o que o operador copia
 * para o suporte quando o endereco nao abre cliente nenhum, e continua visivel
 * mesmo enquanto a consulta carrega ou falha.
 */

import { Link, useParams } from 'react-router-dom';

import { PATHS } from '@/app/paths';
import { ClientDetailView } from '@/features/clients/ClientDetailView';

export function ClientDetailPage() {
  const { clientId } = useParams<{ clientId: string }>();

  return (
    <section className="page">
      <header className="page__header">
        <h1 className="page__title">Detalhe do cliente</h1>
        <p className="page__requirements">
          <span className="tag">RF01</span>
        </p>
      </header>

      {clientId === undefined ? (
        <p className="page__pending">Cliente nao informado no endereco.</p>
      ) : (
        <>
          <p className="page__description">Identificador: {clientId}</p>
          <ClientDetailView clientId={clientId} />
        </>
      )}

      <p className="page__description">
        <Link to={PATHS.clients}>Voltar para a lista de clientes</Link>
      </p>
    </section>
  );
}
