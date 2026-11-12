/**
 * Sessao do operador (RF26).
 *
 * O token fica em `sessionStorage`: sobrevive a recarregamentos na mesma aba,
 * mas e descartado quando a aba fecha. Ele nunca entra em URL, log ou estado
 * de navegacao. O cliente HTTP mantem uma copia em memoria apenas para montar
 * o cabecalho Authorization.
 */

import { api, getAccessToken, setAccessToken } from '@/services/api';
import type { LoginCredentials, OperatorInfo, TokenResponse } from '@/types/api';

const STORAGE_KEY = 'cursos-corporativos.auth-session.v1';

export interface AuthSession {
  readonly accessToken: string;
  readonly expiresAt: number;
  readonly operator: OperatorInfo;
}

type SessionListener = () => void;

const listeners = new Set<SessionListener>();
let expirationTimer: ReturnType<typeof setTimeout> | null = null;

function isOperator(value: unknown): value is OperatorInfo {
  if (typeof value !== 'object' || value === null) return false;
  const candidate = value as Partial<OperatorInfo>;

  return (
    typeof candidate.id === 'string' &&
    typeof candidate.name === 'string' &&
    typeof candidate.email === 'string' &&
    typeof candidate.role === 'string'
  );
}

function isStoredSession(value: unknown): value is AuthSession {
  if (typeof value !== 'object' || value === null) return false;
  const candidate = value as Partial<AuthSession>;

  return (
    typeof candidate.accessToken === 'string' &&
    candidate.accessToken !== '' &&
    typeof candidate.expiresAt === 'number' &&
    Number.isFinite(candidate.expiresAt) &&
    isOperator(candidate.operator)
  );
}

function readStoredSession(): AuthSession | null {
  if (typeof window === 'undefined') return null;

  const serialized = window.sessionStorage.getItem(STORAGE_KEY);
  if (serialized === null) return null;

  try {
    const candidate: unknown = JSON.parse(serialized);
    if (isStoredSession(candidate) && candidate.expiresAt > Date.now()) {
      return candidate;
    }
  } catch {
    // Entrada corrompida ou de uma versao antiga e tratada como sessao ausente.
  }

  window.sessionStorage.removeItem(STORAGE_KEY);
  return null;
}

let currentSession: AuthSession | null = readStoredSession();
setAccessToken(currentSession?.accessToken ?? null);

function emitChange(): void {
  listeners.forEach((listener) => listener());
}

function cancelExpiration(): void {
  if (expirationTimer !== null) {
    clearTimeout(expirationTimer);
    expirationTimer = null;
  }
}

function scheduleExpiration(): void {
  cancelExpiration();
  if (currentSession === null) return;

  const delay = Math.max(0, currentSession.expiresAt - Date.now());
  expirationTimer = setTimeout(() => logout(), delay);
}

function storeSession(session: AuthSession): void {
  currentSession = session;
  setAccessToken(session.accessToken);
  if (typeof window !== 'undefined') {
    window.sessionStorage.setItem(STORAGE_KEY, JSON.stringify(session));
  }
  scheduleExpiration();
  emitChange();
}

scheduleExpiration();

/** Troca credenciais pelo token e inicia a sessao na aba atual. */
export async function login(credentials: LoginCredentials): Promise<AuthSession> {
  const response = await api.post<TokenResponse, LoginCredentials>('/auth/login', credentials);
  const session: AuthSession = {
    accessToken: response.access_token,
    expiresAt: Date.now() + response.expires_in * 1_000,
    operator: response.operator,
  };

  storeSession(session);
  return session;
}

/** Encerra a sessao local sem fazer chamada de rede. */
export function logout(): void {
  cancelExpiration();
  currentSession = null;
  setAccessToken(null);
  if (typeof window !== 'undefined') {
    window.sessionStorage.removeItem(STORAGE_KEY);
  }
  emitChange();
}

/** Sessao corrente, usada para exibir o operador autenticado. */
export function getAuthSession(): AuthSession | null {
  return currentSession;
}

/** Indica se ha token ativo; separado para o guarda e para testes de rota. */
export function hasAuthSession(): boolean {
  return getAccessToken() !== null;
}

/** Assina mudancas de login, logout e expiracao. */
export function subscribeAuthSession(listener: SessionListener): () => void {
  listeners.add(listener);
  return () => listeners.delete(listener);
}
