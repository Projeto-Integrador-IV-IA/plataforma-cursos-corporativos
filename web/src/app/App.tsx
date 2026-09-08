/**
 * Layout base da aplicacao.
 *
 * Estrutura fixa (cabecalho + navegacao lateral) com a area de conteudo
 * preenchida pelo roteador via `Outlet`. Toda tela autenticada e renderizada
 * dentro deste layout; `/login` fica fora dele.
 *
 * TODO(RF17): acomodar aqui o indicador global de progresso da estruturacao
 * por IA, que precisa ser visivel sem bloquear a navegacao.
 */

import { Outlet } from 'react-router-dom';

import { AppNav } from '@/components/AppNav';

export function App() {
  return (
    <div className="layout">
      <header className="layout__header">
        <span className="layout__brand">Cursos Corporativos</span>
      </header>
      <div className="layout__body">
        <aside className="layout__sidebar">
          <AppNav />
        </aside>
        <main className="layout__content">
          <Outlet />
        </main>
      </div>
    </div>
  );
}
