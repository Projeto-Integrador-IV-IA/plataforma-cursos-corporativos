/**
 * Tela de autenticacao (RF26).
 *
 * Unica rota publica da aplicacao: todas as demais exigem sessao (RNF10).
 *
 * Depois do login, o operador volta ao destino privado que tentou abrir.
 */

import { type FormEvent, useId, useState } from "react";
import { Navigate, useLocation, useNavigate } from "react-router-dom";

import { PATHS } from "@/app/paths";
import { useFeedback } from "@/hooks/useFeedback";
import { isApiError } from "@/services/api";
import { hasAuthSession, login } from "@/services/auth";

import "./login.css";

type IconName = "mail" | "lock" | "eye" | "eye-off";

function Icon({ name }: { readonly name: IconName }) {
  const paths: Record<IconName, string> = {
    mail: "M4 5h16v14H4z M4 6l8 6 8-6",
    lock: "M6 10h12v10H6z M8 10V7a4 4 0 0 1 8 0v3 M12 14v2",
    eye: "M2 12s4-7 10-7 10 7 10 7-4 7-10 7S2 12 2 12 M15 12a3 3 0 1 1-6 0 3 3 0 0 1 6 0",
    "eye-off":
      "M3 3l18 18 M10 5a12 12 0 0 1 12 7s-1 2-3 4 M6 6a18 18 0 0 0-4 6s4 7 10 7a12 12 0 0 0 5-1 M10 10a3 3 0 0 0 4 4",
  };
  return (
    <svg
      className="login-icon"
      viewBox="0 0 24 24"
      fill="none"
      stroke="currentColor"
      strokeWidth="1.6"
      strokeLinecap="round"
      strokeLinejoin="round"
      aria-hidden="true"
    >
      <path d={paths[name]} />
    </svg>
  );
}

interface LoginLocationState {
  readonly from?: unknown;
}

interface FieldErrors {
  readonly email?: string;
  readonly password?: string;
}

const LOGIN_FAILURE = "Nao foi possivel entrar. Tente novamente.";

function intendedDestination(state: unknown): string {
  if (typeof state !== "object" || state === null) return PATHS.home;
  const from = (state as LoginLocationState).from;

  return typeof from === "string" &&
    from.startsWith("/") &&
    !from.startsWith("//") &&
    from !== PATHS.login
    ? from
    : PATHS.home;
}

export function LoginPage() {
  const navigate = useNavigate();
  const location = useLocation();
  const { showError } = useFeedback();
  const emailId = useId();
  const passwordId = useId();
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [errors, setErrors] = useState<FieldErrors>({});
  const [submitting, setSubmitting] = useState(false);
  const [showPassword, setShowPassword] = useState(false);
  const destination = intendedDestination(location.state);

  if (hasAuthSession()) {
    return <Navigate to={destination} replace />;
  }

  async function handleSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    const nextErrors: FieldErrors = {
      ...(email.trim() === "" ? { email: "Informe o e-mail." } : {}),
      ...(password === "" ? { password: "Informe a senha." } : {}),
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
      <section className="login-story" aria-labelledby="login-story-title">
        <div className="login-brand">
          <span className="login-brand__initials" aria-hidden="true">
            CC
          </span>
          <span>Cursos Corporativos</span>
        </div>

        <div className="login-story__content">
          <h2 id="login-story-title">
            Cursos que fazem
            <br />
            sentido para cada <span>empresa.</span>
          </h2>
          <p className="login-story__description">
            Organize clientes, demandas e propostas em um só lugar.
          </p>
          <div className="login-story-detail" aria-hidden="true">
            <span className="login-story-detail__circle login-story-detail__circle--large" />
            <span className="login-story-detail__circle login-story-detail__circle--medium" />
            <span className="login-story-detail__circle login-story-detail__circle--small" />
          </div>
        </div>

        <p className="login-story__footer">Gestão de cursos corporativos</p>
      </section>

      <div className="login-workspace">
        <div className="login-workspace__top">
          <span>Cursos Corporativos</span>
        </div>
        <section className="login-card" aria-labelledby="login-title">
          <p className="login-card__welcome">ACESSO À PLATAFORMA</p>
          <h1 id="login-title" className="login-card__title">
            Entrar
          </h1>
          <p className="login-card__description">
            Entre com seu e-mail e senha para continuar.
          </p>

          <form
            className="login-form"
            onSubmit={handleSubmit}
            noValidate
            aria-busy={submitting}
          >
            <div className="form__field">
              <label className="form__label" htmlFor={emailId}>
                E-mail
              </label>
              <div className="login-input">
                <Icon name="mail" />
                <input
                  id={emailId}
                  className="form__control"
                  type="email"
                  placeholder="voce@empresa.com.br"
                  autoCapitalize="none"
                  spellCheck={false}
                  value={email}
                  autoComplete="username"
                  required
                  aria-invalid={errors.email !== undefined}
                  aria-describedby={
                    errors.email === undefined ? undefined : `${emailId}-error`
                  }
                  disabled={submitting}
                  onChange={(event) => {
                    setEmail(event.target.value);
                    if (errors.email !== undefined)
                      setErrors((current) => ({
                        ...current,
                        email: undefined,
                      }));
                  }}
                />
              </div>
              {errors.email !== undefined && (
                <p
                  id={`${emailId}-error`}
                  className="form__hint form__hint--error"
                >
                  {errors.email}
                </p>
              )}
            </div>

            <div className="form__field">
              <label className="form__label" htmlFor={passwordId}>
                Senha
              </label>
              <div className="login-input">
                <Icon name="lock" />
                <input
                  id={passwordId}
                  className="form__control"
                  type={showPassword ? "text" : "password"}
                  placeholder="Digite sua senha"
                  value={password}
                  maxLength={72}
                  autoComplete="current-password"
                  required
                  aria-invalid={errors.password !== undefined}
                  aria-describedby={
                    errors.password === undefined
                      ? undefined
                      : `${passwordId}-error`
                  }
                  disabled={submitting}
                  onChange={(event) => {
                    setPassword(event.target.value);
                    if (errors.password !== undefined)
                      setErrors((current) => ({
                        ...current,
                        password: undefined,
                      }));
                  }}
                />
                <button
                  className="login-password-toggle"
                  type="button"
                  aria-label={showPassword ? "Ocultar senha" : "Mostrar senha"}
                  aria-pressed={showPassword}
                  aria-controls={passwordId}
                  disabled={submitting}
                  onClick={() => setShowPassword((current) => !current)}
                >
                  <Icon name={showPassword ? "eye-off" : "eye"} />
                </button>
              </div>
              {errors.password !== undefined && (
                <p
                  id={`${passwordId}-error`}
                  className="form__hint form__hint--error"
                >
                  {errors.password}
                </p>
              )}
            </div>

            <button
              className="login-submit"
              type="submit"
              disabled={submitting}
            >
              {submitting ? "Entrando..." : "Entrar"}
              {submitting ? (
                <span className="login-spinner" aria-hidden="true" />
              ) : null}
            </button>
          </form>
          <p className="login-card__access">
            <Icon name="lock" /> Acesso exclusivo para operadores cadastrados.
          </p>
          <div className="login-card__help">
            <span>Primeiro acesso ou precisa de ajuda?</span>
            <p>Fale com o administrador da sua organização.</p>
          </div>
        </section>
        <footer className="login-workspace__footer">
          Ambiente interno · Cursos Corporativos
        </footer>
      </div>
    </main>
  );
}
