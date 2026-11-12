/**
 * Sinal visual e acessivel de uma operacao assincrona em curso.
 *
 * A mensagem fica presente enquanto a operacao aguarda a API. A conclusao e
 * comunicada pelo feedback de sucesso ou erro da operacao.
 */

interface ProcessingMessageProps {
  /** Acao que esta sendo executada, em linguagem do operador. */
  operation: string;
}

export function ProcessingMessage({ operation }: ProcessingMessageProps) {
  // `status` nao calcula o nome acessivel a partir do conteudo (regra da ARIA):
  // sem `aria-label`, leitores de tela anunciam a mudanca sem dizer o que
  // esta em andamento.
  return (
    <p
      className="processing-message"
      role="status"
      aria-live="polite"
      aria-busy="true"
      aria-label={`Processando: ${operation}…`}
    >
      <span className="processing-message__mark" aria-hidden="true">
        …
      </span>
      Processando: {operation}…
    </p>
  );
}
