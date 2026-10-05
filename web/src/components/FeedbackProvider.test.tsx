/**
 * Cobre o criterio de aceite do card #84: mensagem unica de sucesso e erro,
 * disparavel de qualquer tela sem prop drilling, com dispensa manual e por
 * tempo.
 *
 * O componente que dispara (`TriggerButtons`) e renderizado tres niveis abaixo
 * do provedor e nao recebe prop nenhuma — e exatamente isso que o teste de
 * prop drilling verifica.
 */

import { act, render, screen, within } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';

import { Providers } from '@/app/providers';
import { FEEDBACK_DURATION_MS } from '@/hooks/feedbackContext';
import { useFeedback } from '@/hooks/useFeedback';

const SUCESSO = 'Cliente cadastrado.';
const ERRO = 'Falha ao cadastrar o cliente.';

function TriggerButtons() {
  const { showSuccess, showError } = useFeedback();

  return (
    <>
      <button type="button" onClick={() => showSuccess(SUCESSO)}>
        Salvar
      </button>
      <button type="button" onClick={() => showError(ERRO)}>
        Falhar
      </button>
    </>
  );
}

/** Tela qualquer: o disparo nasce no fundo da arvore, sem passar props. */
function NestedScreen() {
  return (
    <div>
      <section>
        <article>
          <TriggerButtons />
        </article>
      </section>
    </div>
  );
}

function renderApp() {
  const usuario = userEvent.setup({ advanceTimers: vi.advanceTimersByTime });

  render(
    <Providers>
      <NestedScreen />
    </Providers>,
  );

  return usuario;
}

function regiaoDeSucesso(): HTMLElement {
  return screen.getByRole('status');
}

function regiaoDeErro(): HTMLElement {
  return screen.getByRole('alert');
}

describe('mensagens de sucesso e erro', () => {
  beforeEach(() => {
    // `shouldAdvanceTime` mantem o relogio falso andando sozinho: sem isso o
    // `userEvent`, que espera seus proprios temporizadores entre eventos,
    // nunca retorna. O avanco explicito do teste continua valendo.
    vi.useFakeTimers({ shouldAdvanceTime: true });
  });

  afterEach(() => {
    vi.useRealTimers();
  });

  it('exibe a mensagem de sucesso na regiao anunciada de forma educada', async () => {
    const usuario = renderApp();

    await usuario.click(screen.getByRole('button', { name: 'Salvar' }));

    const mensagem = within(regiaoDeSucesso()).getByText(SUCESSO);
    expect(mensagem).toBeDefined();
    expect(regiaoDeSucesso().getAttribute('aria-live')).toBe('polite');
    expect(mensagem.closest('.feedback')?.getAttribute('data-tone')).toBe('success');
  });

  it('exibe a mensagem de erro na regiao anunciada de forma assertiva', async () => {
    const usuario = renderApp();

    await usuario.click(screen.getByRole('button', { name: 'Falhar' }));

    const mensagem = within(regiaoDeErro()).getByText(ERRO);
    expect(mensagem).toBeDefined();
    expect(regiaoDeErro().getAttribute('aria-live')).toBe('assertive');
    expect(mensagem.closest('.feedback')?.getAttribute('data-tone')).toBe('error');
  });

  it('dispensa a mensagem pelo botao de fechar acionado por teclado', async () => {
    const usuario = renderApp();
    await usuario.click(screen.getByRole('button', { name: 'Salvar' }));

    const fechar = screen.getByRole('button', { name: `Fechar mensagem: ${SUCESSO}` });
    fechar.focus();
    await usuario.keyboard('{Enter}');

    expect(screen.queryByText(SUCESSO)).toBeNull();
  });

  it('dispensa todas as mensagens visiveis com a tecla Esc', async () => {
    const usuario = renderApp();
    await usuario.click(screen.getByRole('button', { name: 'Salvar' }));
    await usuario.click(screen.getByRole('button', { name: 'Falhar' }));

    await usuario.keyboard('{Escape}');

    expect(screen.queryByText(SUCESSO)).toBeNull();
    expect(screen.queryByText(ERRO)).toBeNull();
  });

  it('dispensa a mensagem automaticamente ao fim do tempo padrao', async () => {
    const usuario = renderApp();
    await usuario.click(screen.getByRole('button', { name: 'Salvar' }));

    act(() => {
      vi.advanceTimersByTime(FEEDBACK_DURATION_MS.success / 2);
    });
    expect(screen.queryByText(SUCESSO)).not.toBeNull();

    act(() => {
      vi.advanceTimersByTime(FEEDBACK_DURATION_MS.success);
    });
    expect(screen.queryByText(SUCESSO)).toBeNull();
  });

  it('mantem o erro em tela depois do tempo de um sucesso', async () => {
    const usuario = renderApp();
    await usuario.click(screen.getByRole('button', { name: 'Salvar' }));
    await usuario.click(screen.getByRole('button', { name: 'Falhar' }));

    act(() => {
      vi.advanceTimersByTime(FEEDBACK_DURATION_MS.success);
    });

    expect(screen.queryByText(SUCESSO)).toBeNull();
    expect(screen.queryByText(ERRO)).not.toBeNull();

    act(() => {
      vi.advanceTimersByTime(FEEDBACK_DURATION_MS.error);
    });

    expect(screen.queryByText(ERRO)).toBeNull();
  });

  it('e disparada por componente aninhado que nao recebe prop alguma', async () => {
    const usuario = renderApp();

    // O gatilho esta tres niveis abaixo do provedor e so conhece o hook.
    const gatilho = screen.getByRole('button', { name: 'Salvar' });
    expect(gatilho.closest('article')).not.toBeNull();

    await usuario.click(gatilho);

    expect(within(regiaoDeSucesso()).getByText(SUCESSO)).toBeDefined();
  });

  it('empilha mensagens sucessivas sem sobrescrever a anterior', async () => {
    const usuario = renderApp();

    await usuario.click(screen.getByRole('button', { name: 'Salvar' }));
    await usuario.click(screen.getByRole('button', { name: 'Salvar' }));

    expect(within(regiaoDeSucesso()).getAllByText(SUCESSO)).toHaveLength(2);
  });
});

describe('contrato do hook', () => {
  it('falha de forma explicita quando usado fora do provedor', () => {
    function ForaDoProvedor() {
      useFeedback();
      return null;
    }

    // O React registra o erro do render no console; silenciar mantem a saida
    // do teste legivel sem esconder a asercao.
    const consoleError = vi.spyOn(console, 'error').mockImplementation(() => {});

    expect(() => render(<ForaDoProvedor />)).toThrow(/FeedbackProvider/);

    consoleError.mockRestore();
  });
});
