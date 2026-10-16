/**
 * Criterios de aceite do quadro do pipeline (RF05, card #93).
 *
 * Os testes falam com a tela pelo que o operador ve - titulo da coluna,
 * contagem da etapa, frase da coluna vazia - e dublam a fronteira de rede
 * (`services/pipeline`), nao o `fetch`: e ali que mora o contrato desta tela.
 *
 * A ordem das colunas e do servidor. O que se verifica aqui e que o quadro nao
 * a recalcula: quando o servico devolve as etapas em outra ordem, a tela segue
 * a dele, porque a sequencia do pipeline e regra do pipeline-service e nao
 * pode ter uma segunda copia no frontend.
 *
 * A rolagem contida e, em parte, CSS (`overflow-x` em
 * `.pipeline-board__viewport`), que o jsdom nao calcula. O que o teste cobre e
 * a parte verificavel: existe uma area propria, anunciada e alcancavel pelo
 * teclado, e as colunas estao dentro dela - e nao soltas no corpo da pagina.
 */

import { screen, waitFor, within } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { beforeEach, describe, expect, it, vi } from 'vitest';

import { ApiError } from '@/services/api';
import type {
  PipelineBoard,
  PipelineBoardParams,
  PipelineCardRead,
  PipelineStage,
  PipelineStageGroup,
} from '@/types/api';

vi.mock('@/services/pipeline', () => ({ getPipelineBoard: vi.fn() }));

const { getPipelineBoard } = await import('@/services/pipeline');
const { renderRoute } = await import('@/test/renderRoute');

/** Ordem em que o servico devolve as etapas, conforme o contrato. */
const STAGE_ORDER: readonly PipelineStage[] = [
  'CAPTACAO',
  'ESTRUTURACAO',
  'PRODUTO',
  'PROPOSTA',
  'ACOMPANHAMENTO',
];

/** Os mesmos rotulos, como a coluna os escreve. */
const STAGE_TITLES: readonly string[] = [
  'Captacao',
  'Estruturacao',
  'Produto',
  'Proposta',
  'Acompanhamento',
];

/** Cartoes carregados por coluna, declarado na tela. */
const CARDS_PER_STAGE = 20;

type CardsByStage = Partial<Record<PipelineStage, readonly PipelineCardRead[]>>;
type TotalsByStage = Partial<Record<PipelineStage, number>>;

function createCard(number: number, partial: Partial<PipelineCardRead> = {}): PipelineCardRead {
  const label = String(number).padStart(2, '0');

  return {
    id: `demanda-${label}`,
    title: `Demanda ${label}`,
    status: 'ABERTA',
    client: { id: `cliente-${label}`, name: `Cliente ${label}` },
    owner: { id: 'responsavel-01', name: 'Marina Prado' },
    created_at: '2026-09-20T09:00:00-03:00',
    updated_at: '2026-09-20T09:00:00-03:00',
    ...partial,
  };
}

/**
 * Quadro como o servico o devolve: as cinco etapas sempre presentes, cada uma
 * com seus cartoes e o total real da etapa. `totals` existe para simular o
 * recorte por coluna, em que o total e maior que os cartoes recebidos.
 */
function createBoard(
  cards: CardsByStage,
  totals: TotalsByStage = {},
  order: readonly PipelineStage[] = STAGE_ORDER,
): PipelineBoard {
  const stages: PipelineStageGroup[] = order.map((stage) => {
    const items = cards[stage] ?? [];

    return { stage, total: totals[stage] ?? items.length, items };
  });

  return { stages, total: stages.reduce((sum, group) => sum + group.total, 0) };
}

function withBoard(board: PipelineBoard) {
  vi.mocked(getPipelineBoard).mockResolvedValue(board);
}

function lastParams(): PipelineBoardParams {
  const calls = vi.mocked(getPipelineBoard).mock.calls;

  return calls[calls.length - 1]?.[0] ?? {};
}

function column(name: string): HTMLElement {
  return screen.getByRole('region', { name });
}

function columnTitles(): readonly (string | null)[] {
  return screen.getAllByRole('heading', { level: 2 }).map((heading) => heading.textContent);
}

beforeEach(() => {
  vi.clearAllMocks();
  withBoard(
    createBoard({
      CAPTACAO: [createCard(1), createCard(2)],
      ESTRUTURACAO: [createCard(3)],
      ACOMPANHAMENTO: [createCard(4)],
    }),
  );
});

describe('quadro do pipeline', () => {
  it('apresenta as cinco etapas na ordem devolvida pelo servico', async () => {
    renderRoute('/pipeline');
    await screen.findByRole('heading', { level: 2, name: 'Captacao' });

    expect(columnTitles()).toEqual(STAGE_TITLES);
  });

  it('segue a ordem do servico em vez de reordenar as colunas por conta propria', async () => {
    const reversed = [...STAGE_ORDER].reverse();
    withBoard(createBoard({ CAPTACAO: [createCard(1)] }, {}, reversed));
    renderRoute('/pipeline');
    await screen.findByRole('heading', { level: 2, name: 'Captacao' });

    expect(columnTitles()).toEqual([...STAGE_TITLES].reverse());
  });

  it('coloca cada demanda na coluna da sua etapa', async () => {
    withBoard(
      createBoard({
        CAPTACAO: [createCard(1, { title: 'Integracao de novos gestores' })],
        ESTRUTURACAO: [createCard(2, { title: 'Treinamento de NR-12' })],
      }),
    );
    renderRoute('/pipeline');
    await screen.findByRole('heading', { level: 2, name: 'Captacao' });

    expect(
      within(column('Estruturacao')).getByRole('link', { name: /Treinamento de NR-12/ }),
    ).toBeDefined();
    expect(
      within(column('Captacao')).queryByRole('link', { name: /Treinamento de NR-12/ }),
    ).toBeNull();
  });

  it('da apresentacao propria a etapa sem demanda, em vez de omitir a coluna', async () => {
    renderRoute('/pipeline');
    await screen.findByRole('heading', { level: 2, name: 'Produto' });

    const empty = column('Produto');

    expect(within(empty).getByText('Nenhuma demanda nesta etapa.')).toBeDefined();
    expect(within(empty).getByText('0 demandas')).toBeDefined();
    expect(within(empty).queryByRole('link')).toBeNull();
  });

  it('conta a etapa inteira no cabecalho, mesmo quando o recorte nao trouxe todas', async () => {
    withBoard(
      createBoard({ CAPTACAO: [createCard(1), createCard(2)] }, { CAPTACAO: 34 }),
    );
    renderRoute('/pipeline');
    await screen.findByRole('heading', { level: 2, name: 'Captacao' });

    expect(within(column('Captacao')).getByText('Mostrando 2 de 34 demandas')).toBeDefined();
  });

  it('contem a rolagem horizontal numa area propria, alcancavel pelo teclado', async () => {
    renderRoute('/pipeline');
    const viewport = await screen.findByRole('group', { name: /rolagem horizontal/i });

    expect(viewport.tabIndex).toBe(0);
    // As colunas moram dentro da area rolavel: e ela que rola, nao a pagina.
    for (const title of STAGE_TITLES) {
      expect(viewport.contains(column(title))).toBe(true);
    }
  });

  it('pede ao servico o recorte por coluna que a tela anuncia', async () => {
    renderRoute('/pipeline');
    await screen.findByRole('heading', { level: 2, name: 'Captacao' });

    // Somente o recorte: nenhum filtro de etapa, que o servico recusa com 422
    // e `PipelineBoardParams` nem permite expressar.
    expect(lastParams()).toEqual({ limit: CARDS_PER_STAGE });
  });

  it('trata quadro vazio convidando a abrir a primeira negociacao, sem perder as colunas', async () => {
    withBoard(createBoard({}));
    renderRoute('/pipeline');

    expect(await screen.findByText(/Nenhuma demanda no pipeline ate agora/)).toBeDefined();
    expect(screen.getByRole('link', { name: 'Abra a primeira negociacao' })).toBeDefined();
    expect(columnTitles()).toEqual(STAGE_TITLES);
  });

  it('mostra a mensagem da API quando o quadro falha, com opcao de repetir', async () => {
    const user = userEvent.setup();
    vi.mocked(getPipelineBoard).mockRejectedValue(
      new ApiError({
        kind: 'http',
        code: 'VALIDATION_ERROR',
        message: 'Os dados informados sao invalidos.',
        status: 422,
      }),
    );
    renderRoute('/pipeline');

    // A regiao global de mensagens ja ocupa o unico `role="alert"` da tela,
    // entao o aviso local se anuncia por `aria-live`: a busca parte do texto e
    // confirma que ele esta dentro de uma regiao assertiva.
    const warning = await screen.findByText(
      'Os dados informados sao invalidos.',
      {},
      { timeout: 3000 },
    );

    expect(warning.closest('[aria-live="assertive"]')).not.toBeNull();
    expect(screen.queryByRole('heading', { level: 2, name: 'Captacao' })).toBeNull();

    withBoard(createBoard({ CAPTACAO: [createCard(1)] }));
    await user.click(screen.getByRole('button', { name: 'Tentar novamente' }));

    await waitFor(() => expect(columnTitles()).toEqual(STAGE_TITLES));
  });
});
