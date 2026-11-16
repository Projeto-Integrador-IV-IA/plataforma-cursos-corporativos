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

import { Link } from "react-router-dom";

import { PATHS } from "@/app/paths";
import { PermissionGate } from "@/features/auth/Authorization";
import { PERMISSIONS } from "@/features/auth/permissions";
import { ClientList } from "@/features/clients/ClientList";

import "./clients.css";

export function ClientsPage() {
  return (
    <section className="page">
      <header className="clients-page__header">
        <div>
          <h1 className="page__title">Clientes</h1>
          <p className="page__description">
            Empresas cadastradas na plataforma.
          </p>
        </div>
        <PermissionGate permission={PERMISSIONS.clientsManage}>
          <Link className="button clients-page__create" to={PATHS.clientNew}>
            <span aria-hidden="true">+</span> Cadastrar cliente
          </Link>
        </PermissionGate>
      </header>
      <ClientList />
    </section>
  );
}
