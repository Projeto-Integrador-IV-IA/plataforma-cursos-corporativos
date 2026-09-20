/**
 * Contrato das mensagens de sucesso e erro da aplicacao.
 *
 * Fica separado do provedor e do hook de proposito: o contexto e os tipos sao
 * dados puros, entao componentes, hook e testes importam daqui sem arrastar a
 * arvore de componentes junto.
 *
 * O estado vive em um unico provedor montado na raiz (`FeedbackProvider`), o
 * que permite disparar mensagem de qualquer tela sem prop drilling.
 */

import { createContext } from 'react';

/** Natureza da mensagem: decide cor, icone e urgencia do anuncio. */
export type FeedbackTone = 'success' | 'error';

/** Uma mensagem em exibicao. */
export interface FeedbackItem {
  /** Identificador interno, usado como chave de lista e alvo da dispensa. */
  id: string;
  tone: FeedbackTone;
  /** Texto exibido ao usuario, ja em portugues e pronto para leitura. */
  text: string;
}

/** API exposta pelo hook `useFeedback`. */
export interface FeedbackContextValue {
  /** Mensagens visiveis no momento, da mais antiga para a mais recente. */
  items: readonly FeedbackItem[];
  /** Exibe uma confirmacao de operacao bem-sucedida. */
  showSuccess: (text: string) => void;
  /** Exibe uma falha que o usuario precisa conhecer. */
  showError: (text: string) => void;
  /** Remove uma mensagem especifica antes do tempo acabar. */
  dismiss: (id: string) => void;
  /** Remove todas as mensagens visiveis (usado pela tecla Esc). */
  dismissAll: () => void;
}

/**
 * Tempo de exibicao padrao, em milissegundos.
 *
 * Erro fica mais tempo que sucesso porque costuma trazer instrucao a ler; o
 * sucesso apenas confirma uma acao que o usuario acabou de executar. Os dois
 * valores sao unicos na aplicacao: nenhuma tela define duracao propria.
 */
export const FEEDBACK_DURATION_MS: Record<FeedbackTone, number> = {
  success: 4000,
  error: 8000,
};

export const FeedbackContext = createContext<FeedbackContextValue | null>(null);
