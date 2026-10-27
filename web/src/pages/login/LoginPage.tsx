/**
 * Tela de autenticacao (RF26).
 *
 * Unica rota publica da aplicacao: todas as demais exigem sessao (RNF10).
 *
 * Depois do login, o operador volta ao destino privado que tentou abrir.
 */

import { type FormEvent, useId, useState } from 'react';
import { Navigate, useLocation, useNavigate } from 'react-router-dom';

import { PATHS } from '@/app/paths';
import { useFeedback } from '@/hooks/useFeedback';
import { isApiError } from '@/services/api';
import { hasAuthSession, login } from '@/services/auth';

interface LoginLocationState {
  readonly from?: unknown;
}

interface FieldErrors {
  readonly email?: string;
  readonly password?: string;
}

const LOGIN_FAILURE = 'Nao foi possivel entrar. Tente novamente.';

function intendedDestination(state: unknown): string {
  if (typeof state !== 'object' || state === null) return PATHS.clients;
  const from = (state as LoginLocationState).from;

  return typeof from === 'string' &&
    from.startsWith('/') &&
    !from.startsWith('//') &&
    from !== PATHS.login
    ? from
    : PATHS.clients;
}

export function LoginPage() {
  const navigate = useNavigate();
  const location = useLocation();
  const { showError } = useFeedback();
  const emailId = useId();
  const passwordId = useId();
  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
  const [errors, setErrors] = useState<FieldErrors>({});
  const [submitting, setSubmitting] = useState(false);
  const destination = intendedDestination(location.state);

  if (hasAuthSession()) {
    return <Navigate to={destination} replace />;
  }

  async function handleSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    const nextErrors: FieldErrors = {
      ...(email.trim() === '' ? { email: 'Informe o e-mail.' } : {}),
      ...(password === '' ? { password: 'Informe a senha.' } : {}),
    };
    setErrors(nextErrors);

    if (Object.keys(nextErrors).length > 0) return;

    setSubmitting(true);
    try {
      await login({ email: email.trim(), password });
      navigate(destination, { replace: true });
    } catch (error) {
      showError(isApiError(error) ? error.message : LOGIN_FAILURE);
    } finally {
      setSubmitting(false);
    }
  }

  return (
    <main className="login-page">
      <section className="login-card" aria-labelledby="login-title">
        <p className="login-card__brand">Cursos Corporativos</p>
        <h1 id="login-title" className="login-card__title">
          Entrar
        </h1>
        <p className="login-card__description">Use suas credenciais de operador.</p>

        <form className="form" onSubmit={handleSubmit} noValidate>
          <div className="form__field">
            <label className="form__label" htmlFor={emailId}>
              E-mail <abbr title="obrigatorio">*</abbr>
            </label>
            <input
              id={emailId}
              className="form__control"
              type="email"
              value={email}
              autoComplete="username"
              required
              aria-invalid={errors.email !== undefined}
              aria-describedby={errors.email === undefined ? undefined : `${emailId}-error`}
              disabled={submitting}
              onChange={(event) => {
                setEmail(event.target.value);
                if (errors.email !== undefined)
                  setErrors((current) => ({ ...current, email: undefined }));
              }}
            />
            {errors.email !== undefined && (
              <p id={`${emailId}-error`} className="form__hint form__hint--error">
                {errors.email}
              </p>
            )}
          </div>

          <div className="form__field">
            <label className="form__label" htmlFor={passwordId}>
              Senha <abbr title="obrigatorio">*</abbr>
            </label>
            <input
              id={passwordId}
              className="form__control"
              type="password"
              value={password}
              maxLength={72}
              autoComplete="current-password"
              required
              aria-invalid={errors.password !== undefined}
              aria-describedby={errors.password === undefined ? undefined : `${passwordId}-error`}
              disabled={submitting}
              onChange={(event) => {
                setPassword(event.target.value);
                if (errors.password !== undefined)
                  setErrors((current) => ({ ...current, password: undefined }));
              }}
            />
            {errors.password !== undefined && (
              <p id={`${passwordId}-error`} className="form__hint form__hint--error">
                {errors.password}
              </p>
            )}
          </div>

          <div className="form__actions">
            <button className="button" type="submit" disabled={submitting}>
              {submitting ? 'Entrando...' : 'Entrar'}
            </button>
          </div>
        </form>
      </section>
    </main>
  );
}
