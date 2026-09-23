/**
 * Lista de empresas clientes (RF01, RF03).
 *
 * A tela e a moldura: titulo, o acesso ao cadastro (RF01, que ja existe em
 * `/clientes/novo`) e a listagem em si, que mora em
 * `features/clients/ClientList`.
 *
 * TODO(RF03): oferecer busca por nome e recorte por situacao quando
 * `GET /api/v1/clients` passar a aceita-los no contrato (RNF02).
 */

import { Link } from 'react-router-dom';

import { PATHS } from '@/app/paths';
import { ClientList } from '@/features/clients/ClientList';

export function ClientsPage() {
  return (
    <section className="page">
      <header className="page__header">
        <h1 className="page__title">Clientes</h1>
        <p className="page__requirements">
          <span className="tag">RF01</span>
          <span className="tag">RF03</span>
        </p>
      </header>
      <p className="page__description">
        Empresas clientes, da mais recente para a mais antiga.{' '}
        <Link to={PATHS.clientNew}>Cadastrar cliente</Link>
      </p>
      <ClientList />
    </section>
  );
}
