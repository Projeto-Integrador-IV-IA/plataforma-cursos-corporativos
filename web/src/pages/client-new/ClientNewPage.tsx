/**
 * Tela de cadastro de cliente (RF01).
 *
 * Rota propria, pelo mesmo motivo de `/demandas/nova`: a listagem de clientes
 * com filtros e outro card, e dividir a mesma tela entre cadastro e consulta
 * deixaria as duas entregas disputando o mesmo componente. A listagem so leva
 * ate aqui, por link.
 */

import { Link } from 'react-router-dom';

import { PATHS } from '@/app/paths';
import { ClientForm } from '@/features/clients/ClientForm';

export function ClientNewPage() {
  return (
    <section className="page">
      <header className="page__header">
        <h1 className="page__title" id="titulo-novo-cliente">
          Novo cliente
        </h1>
        <p className="page__requirements">
          <span className="tag">RF01</span>
        </p>
        <p className="page__description">
          O cadastro da empresa e o primeiro passo: toda demanda nasce vinculada a um cliente
          (RF02). Apenas a razao social e obrigatoria.
        </p>
      </header>

      <ClientForm />

      <p className="page__description">
        <Link to={PATHS.clients}>Voltar para a lista de clientes</Link>
      </p>
    </section>
  );
}
