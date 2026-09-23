/**
 * Mensagem unica de sucesso ou de erro.
 *
 * E o componente visual compartilhado por toda a aplicacao: nenhuma tela
 * desenha sua propria faixa de aviso, entao sucesso e erro tem a mesma cara em
 * qualquer lugar. Quem dispara usa o hook `useFeedback`; este componente so
 * sabe desenhar e avisar que foi dispensado.
 *
 * O botao de fechar e um `button` real justamente para ser alcancavel por
 * teclado — dispensar a mensagem nao depende de mouse.
 */

import type { FeedbackItem } from '@/hooks/feedbackContext';

interface FeedbackMessageProps {
  item: FeedbackItem;
  /** Chamado quando o usuario fecha a mensagem pelo botao. */
  onDismiss: (id: string) => void;
}

/** Marcador visual por tipo; e decorativo, o texto ja carrega o sentido. */
const TONE_MARK: Record<FeedbackItem['tone'], string> = {
  success: '✓',
  error: '!',
};

export function FeedbackMessage({ item, onDismiss }: FeedbackMessageProps) {
  return (
    <div className={`feedback feedback--${item.tone}`} data-tone={item.tone}>
      <span className="feedback__mark" aria-hidden="true">
        {TONE_MARK[item.tone]}
      </span>
      <span className="feedback__text">{item.text}</span>
      <button
        type="button"
        className="feedback__dismiss"
        aria-label={`Fechar mensagem: ${item.text}`}
        onClick={() => onDismiss(item.id)}
      >
        <span aria-hidden="true">×</span>
      </button>
    </div>
  );
}
