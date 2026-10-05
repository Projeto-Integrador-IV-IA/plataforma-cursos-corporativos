/**
 * Acesso as mensagens de sucesso e erro a partir de qualquer tela.
 *
 * Qualquer componente abaixo dos providers globais chama `useFeedback()` e
 * dispara a mensagem — sem receber callback por prop e sem `alert` nativo.
 *
 * ```tsx
 * const { showSuccess, showError } = useFeedback();
 * showSuccess('Cliente cadastrado.');
 * ```
 */

import { useContext } from 'react';

import { FeedbackContext, type FeedbackContextValue } from '@/hooks/feedbackContext';

export function useFeedback(): FeedbackContextValue {
  const context = useContext(FeedbackContext);

  if (context === null) {
    // Falha alto e cedo: sem o provedor a mensagem sumiria em silencio, que e
    // o pior desfecho possivel para um aviso de erro.
    throw new Error('useFeedback exige um <FeedbackProvider> acima na arvore.');
  }

  return context;
}
