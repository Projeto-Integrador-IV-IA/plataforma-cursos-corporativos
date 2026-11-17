import { type ReactNode, useSyncExternalStore } from 'react';
import { Navigate } from 'react-router-dom';

import { PATHS } from '@/app/paths';
import { AuthSessionContext, hasPermission, useSession, type Permission } from '@/features/auth/permissions';
import { getAuthSession, subscribeAuthSession, type AuthSession } from '@/services/auth';

interface AuthSessionProviderProps {
  readonly session: AuthSession | null;
  readonly children: ReactNode;
}

/**
 * Sobrescreve a sessao externa em testes e renderizadores isolados.
 *
 * Uma sessao real iniciada durante o proprio teste (por exemplo, um login
 * feito pela interface) tem prioridade sobre a sessao fixa passada aqui: sem
 * isso, o restante da arvore ficaria congelado na sessao de antes do login.
 */
export function AuthSessionProvider({ session, children }: AuthSessionProviderProps) {
  const liveSession = useSyncExternalStore(subscribeAuthSession, getAuthSession, () => null);

  return (
    <AuthSessionContext.Provider value={liveSession ?? session}>
      {children}
    </AuthSessionContext.Provider>
  );
}

interface PermissionGateProps {
  readonly permission: Permission;
  readonly children: ReactNode;
}

/** Exibe uma acao somente se o perfil da sessao a permite. */
export function PermissionGate({ permission, children }: PermissionGateProps) {
  const session = useSession();

  return hasPermission(session?.operator.role, permission) ? children : null;
}

type RequirePermissionProps = PermissionGateProps;

/** Bloqueia a rota na interface; a API continua responsavel pela autorizacao efetiva. */
export function RequirePermission({ permission, children }: RequirePermissionProps) {
  const session = useSession();

  if (!hasPermission(session?.operator.role, permission)) {
    return <Navigate to={PATHS.accessDenied} replace />;
  }

  return children;
}
