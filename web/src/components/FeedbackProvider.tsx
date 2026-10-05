/**
 * Provedor das mensagens de sucesso e erro.
 *
 * Guarda a fila de mensagens visiveis e e o unico dono dos temporizadores de
 * dispensa automatica. Montado uma vez em `app/providers.tsx`, faz com que
 * qualquer tela dispare uma mensagem apenas chamando `useFeedback()`.
 *
 * Formas de dispensar, todas equivalentes:
 * - botao de fechar da propria mensagem (alcancavel por teclado);
 * - tecla `Esc`, que limpa o que estiver na tela;
 * - tempo, conforme `FEEDBACK_DURATION_MS`.
 */

import { type ReactNode, useCallback, useEffect, useMemo, useRef, useState } from 'react';

import { FeedbackRegion } from '@/components/FeedbackRegion';
import {
  FEEDBACK_DURATION_MS,
  FeedbackContext,
  type FeedbackContextValue,
  type FeedbackItem,
  type FeedbackTone,
} from '@/hooks/feedbackContext';

interface FeedbackProviderProps {
  children: ReactNode;
}

export function FeedbackProvider({ children }: FeedbackProviderProps) {
  const [items, setItems] = useState<readonly FeedbackItem[]>([]);
  // Contador local em vez de identificador aleatorio: basta ser unico dentro
  // da montagem e mantem o teste deterministico.
  const lastId = useRef(0);
  const timers = useRef(new Map<string, ReturnType<typeof setTimeout>>());

  const dismiss = useCallback((id: string) => {
    const timer = timers.current.get(id);

    if (timer !== undefined) {
      clearTimeout(timer);
      timers.current.delete(id);
    }

    setItems((current) => current.filter((item) => item.id !== id));
  }, []);

  const dismissAll = useCallback(() => {
    timers.current.forEach((timer) => clearTimeout(timer));
    timers.current.clear();
    setItems([]);
  }, []);

  const show = useCallback(
    (tone: FeedbackTone, text: string) => {
      lastId.current += 1;
      const id = `feedback-${lastId.current}`;

      setItems((current) => [...current, { id, tone, text }]);
      timers.current.set(
        id,
        setTimeout(() => dismiss(id), FEEDBACK_DURATION_MS[tone]),
      );
    },
    [dismiss],
  );

  const showSuccess = useCallback((text: string) => show('success', text), [show]);
  const showError = useCallback((text: string) => show('error', text), [show]);

  // O atalho so existe enquanto ha mensagem: sem isso, cada Esc na aplicacao
  // provocaria um render inutil.
  useEffect(() => {
    if (items.length === 0) {
      return;
    }

    function handleKeyDown(event: KeyboardEvent) {
      if (event.key === 'Escape') {
        dismissAll();
      }
    }

    window.addEventListener('keydown', handleKeyDown);

    return () => window.removeEventListener('keydown', handleKeyDown);
  }, [items.length, dismissAll]);

  // Desmontagem no meio da contagem deixaria temporizador orfao tentando
  // atualizar estado de uma arvore que nao existe mais.
  useEffect(() => {
    const pending = timers.current;

    return () => {
      pending.forEach((timer) => clearTimeout(timer));
      pending.clear();
    };
  }, []);

  const value = useMemo<FeedbackContextValue>(
    () => ({ items, showSuccess, showError, dismiss, dismissAll }),
    [items, showSuccess, showError, dismiss, dismissAll],
  );

  return (
    <FeedbackContext.Provider value={value}>
      {children}
      <FeedbackRegion items={items} onDismiss={dismiss} />
    </FeedbackContext.Provider>
  );
}
