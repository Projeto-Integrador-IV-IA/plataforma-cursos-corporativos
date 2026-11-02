/** Guarda das rotas privadas e tratamento central de sessao expirada (RF26). */

import { type ReactNode, useEffect, useSyncExternalStore } from 'react';
import { Navigate, useLocation, useNavigate } from 'react-router-dom';

import { PATHS } from '@/app/paths';
import { useFeedback } from '@/hooks/useFeedback';
import { onUnauthorized } from '@/services/api';
import { hasAuthSession, logout, subscribeAuthSession } from '@/services/auth';

interface RequireSessionProps {
  children: ReactNode;
}

function currentDestination(pathname: string, search: string, hash: string): string {
  return `${pathname}${search}${hash}`;
}

export function RequireSession({ children }: RequireSessionProps) {
  const authenticated = useSyncExternalStore(subscribeAuthSession, hasAuthSession, hasAuthSession);
  const location = useLocation();
  const navigate = useNavigate();
  const { showError } = useFeedback();
  const destination = currentDestination(location.pathname, location.search, location.hash);

  useEffect(
    () =>
      onUnauthorized(() => {
        logout();
        showError('Sua sessao expirou. Entre novamente para continuar.');
        navigate(PATHS.login, { replace: true, state: { from: destination } });
      }),
    [destination, navigate, showError],
  );

  if (!authenticated) {
    return <Navigate to={PATHS.login} replace state={{ from: destination }} />;
  }

  return children;
}
