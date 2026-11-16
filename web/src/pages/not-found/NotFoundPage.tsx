/**
 * Rota inexistente.
 *
 * Fecha o mapa de rotas: qualquer caminho fora do previsto cai aqui em vez de
 * renderizar tela em branco.
 */

import { Link } from "react-router-dom";

import { PATHS } from "@/app/paths";
import { PermissionGate } from "@/features/auth/Authorization";
import { PERMISSIONS } from "@/features/auth/permissions";

export function NotFoundPage() {
  return (
    <section className="page">
      <h1 className="page__title">Pagina nao encontrada</h1>
      <p className="page__description">
        O endereco acessado nao corresponde a nenhuma tela.
      </p>
      <PermissionGate permission={PERMISSIONS.pipelineRead}>
        <Link to={PATHS.home}>Voltar para a visão geral</Link>
      </PermissionGate>
    </section>
  );
}
