import { createContext, type ReactNode, useContext, useSyncExternalStore } from 'react';
import { Navigate } from 'react-router-dom';

import { PATHS } from '@/app/paths';
import { getAuthSession, subscribeAuthSession, type AuthSession } from '@/services/auth';

export const PERMISSIONS = {
  clientsRead: 'clients.read',
  clientsManage: 'clients.manage',
  pipelineRead: 'pipeline.read',
  demandsRead: 'demands.read',
  demandsManage: 'demands.manage',
  ingestionCreate: 'ingestion.create',
  structuringReview: 'structuring.review',
  artifactsRead: 'artifacts.read',
} as const;

export type Permission = (typeof PERMISSIONS)[keyof typeof PERMISSIONS];

const ALL_PERMISSIONS = Object.values(PERMISSIONS);

/**
 * O backend do MVP so emite OPERADOR. Papeis futuros nao recebem acesso ate
 * que a matriz oficial de autorizacao por operacao seja publicada.
 */
const ROLE_PERMISSIONS: ReadonlyMap<string, ReadonlySet<Permission>> = new Map([
  ['OPERADOR', new Set<Permission>(ALL_PERMISSIONS)],
]);

const AuthSessionContext = createContext<AuthSession | null | undefined>(undefined);

interface AuthSessionProviderProps {
  readonly session: AuthSession | null;
  readonly children: ReactNode;
}

/** Sobrescreve a sessao externa em testes e renderizadores isolados. */
export function AuthSessionProvider({ session, children }: AuthSessionProviderProps) {
  return <AuthSessionContext.Provider value={session}>{children}</AuthSessionContext.Provider>;
}

function useSession(): AuthSession | null {
  const providedSession = useContext(AuthSessionContext);
  const storedSession = useSyncExternalStore(
    subscribeAuthSession,
    getAuthSession,
    () => null,
  );

  return providedSession === undefined ? storedSession : providedSession;
}

export function useAuthorization() {
  const session = useSession();

  return {
    role: session?.operator.role ?? null,
    can: (permission: Permission) => hasPermission(session?.operator.role, permission),
  };
}

export function hasPermission(role: string | null | undefined, permission: Permission): boolean {
  return (
    role !== null &&
    role !== undefined &&
    (ROLE_PERMISSIONS.get(role)?.has(permission) ?? false)
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
