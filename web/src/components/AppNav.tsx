/**
 * Navegacao principal do operador.
 *
 * Lista apenas as telas de nivel superior; telas de detalhe sao alcancadas a
 * partir delas. `NavLink` marca a rota ativa, entao o estado de navegacao vem
 * do roteador e nao de estado local duplicado.
 */

import { NavLink } from 'react-router-dom';

import { PATHS } from '@/app/paths';

interface NavItem {
  to: string;
  label: string;
}

const NAV_ITEMS: readonly NavItem[] = [
  { to: PATHS.clients, label: 'Clientes' },
  { to: PATHS.demands, label: 'Demandas' },
];

export function AppNav() {
  return (
    <nav className="nav" aria-label="Navegacao principal">
      <ul className="nav__list">
        {NAV_ITEMS.map((item) => (
          <li key={item.to}>
            <NavLink
              to={item.to}
              className={({ isActive }) => (isActive ? 'nav__link nav__link--active' : 'nav__link')}
            >
              {item.label}
            </NavLink>
          </li>
        ))}
      </ul>
    </nav>
  );
}
