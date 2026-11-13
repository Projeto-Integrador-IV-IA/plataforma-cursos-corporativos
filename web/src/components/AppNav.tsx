/**
 * Navegacao principal do operador.
 *
 * Lista apenas as telas de nivel superior; telas de detalhe sao alcancadas a
 * partir delas. `NavLink` marca a rota ativa, entao o estado de navegacao vem
 * do roteador e nao de estado local duplicado.
 */

import { NavLink } from 'react-router-dom';

import { PATHS } from '@/app/paths';
import { PERMISSIONS, hasPermission, useAuthorization } from '@/features/auth/Authorization';

interface NavItem {
  to: string;
  label: string;
  permission: (typeof PERMISSIONS)[keyof typeof PERMISSIONS];
}

const NAV_ITEMS: readonly NavItem[] = [
  { to: PATHS.clients, label: 'Clientes', permission: PERMISSIONS.clientsRead },
  { to: PATHS.pipeline, label: 'Pipeline', permission: PERMISSIONS.pipelineRead },
  { to: PATHS.demands, label: 'Demandas', permission: PERMISSIONS.demandsRead },
];

export function AppNav() {
  const { role } = useAuthorization();
  const visibleItems = NAV_ITEMS.filter((item) => hasPermission(role, item.permission));

  return (
    <nav className="nav" aria-label="Navegacao principal">
      <ul className="nav__list">
        {visibleItems.map((item) => (
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
