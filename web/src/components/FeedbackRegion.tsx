/**
 * Area fixa onde as mensagens aparecem, sobreposta ao conteudo da tela.
 *
 * Sao duas regioes dinamicas (`live regions`) sempre presentes no DOM, e nao
 * criadas junto com a mensagem: leitor de tela so anuncia o que entra em uma
 * regiao que ja existia. Sucesso vai para a regiao educada (`role="status"`),
 * que espera o leitor terminar a frase atual; erro vai para a assertiva
 * (`role="alert"`), que interrompe — o usuario precisa saber que a acao falhou.
 */

import { FeedbackMessage } from '@/components/FeedbackMessage';
import type { FeedbackItem } from '@/hooks/feedbackContext';

interface FeedbackRegionProps {
  items: readonly FeedbackItem[];
  onDismiss: (id: string) => void;
}

export function FeedbackRegion({ items, onDismiss }: FeedbackRegionProps) {
  const successes = items.filter((item) => item.tone === 'success');
  const errors = items.filter((item) => item.tone === 'error');

  return (
    <div className="feedback-region">
      <div
        className="feedback-region__live"
        role="alert"
        aria-live="assertive"
        aria-label="Mensagens de erro"
      >
        {errors.map((item) => (
          <FeedbackMessage key={item.id} item={item} onDismiss={onDismiss} />
        ))}
      </div>
      <div
        className="feedback-region__live"
        role="status"
        aria-live="polite"
        aria-label="Mensagens de sucesso"
      >
        {successes.map((item) => (
          <FeedbackMessage key={item.id} item={item} onDismiss={onDismiss} />
        ))}
      </div>
    </div>
  );
}
