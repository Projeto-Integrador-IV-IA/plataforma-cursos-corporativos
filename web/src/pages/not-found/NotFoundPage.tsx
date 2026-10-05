/**
 * Rota inexistente.
 *
 * Fecha o mapa de rotas: qualquer caminho fora do previsto cai aqui em vez de
 * renderizar tela em branco.
 */

import { Link } from 'react-router-dom';

import { PATHS } from '@/app/paths';

export function NotFoundPage() {
  return (
    <section className="page">
      <h1 className="page__title">Pagina nao encontrada</h1>
      <p className="page__description">O endereco acessado nao corresponde a nenhuma tela.</p>
      <Link to={PATHS.clients}>Voltar para clientes</Link>
    </section>
  );
}
