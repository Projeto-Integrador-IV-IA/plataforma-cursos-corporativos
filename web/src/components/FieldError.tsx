interface FieldErrorProps {
  readonly id: string;
  readonly message?: string;
}

/** Mensagem única para erros pertencentes a um controle de formulário. */
export function FieldError({ id, message }: FieldErrorProps) {
  if (message === undefined) return null;

  return (
    <p id={id} className="form__hint form__hint--error" role="alert">
      {message}
    </p>
  );
}
