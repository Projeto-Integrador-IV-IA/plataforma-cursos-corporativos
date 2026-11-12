/** Sinal visual e acessivel de uma operacao assincrona em curso. */

interface ProcessingMessageProps {
  operation: string;
}

export function ProcessingMessage({ operation }: ProcessingMessageProps) {
  return (
    <p className="processing-message" role="status" aria-live="polite" aria-busy="true">
      <span className="processing-message__mark" aria-hidden="true">
        …
      </span>
      Processando: {operation}…
    </p>
  );
}
