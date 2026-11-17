import { createContext, useContext, useSyncExternalStore } from 'react';

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

export const AuthSessionContext = createContext<AuthSession | null | undefined>(undefined);

export function useSession(): AuthSession | null {
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
