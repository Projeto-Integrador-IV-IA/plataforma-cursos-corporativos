/**
 * Criterios de aceite do cartao da demanda no pipeline (RF05, card #94).
 *
 * O cartao e testado dentro do quadro, na rota `/pipeline`, e nao isolado: e
 * assim que o operador o encontra, e assim o teste cobre tambem o caminho de
 * ida ao detalhe. A fronteira dublada e `services/pipeline`, nao o `fetch`.
 *
 * O que se verifica aqui: os quatro dados minimos (cliente, titulo,
 * responsavel e situacao), o cartao inteiro como alvo de clique para o detalhe
 * da demanda, e o sinal de atencao dito tambem em texto - cor sozinha nao
 * chega a quem nao a distingue nem sobrevive a impressao em preto e branco.
 */

import { screen, within } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { beforeEach, describe, expect, it, vi } from 'vitest';

import type { PipelineBoard, PipelineCardRead, PipelineStage } from '@/types/api';

vi.mock('@/services/pipeline', () => ({ getPipelineBoard: vi.fn() }));

const { getPipelineBoard } = await import('@/services/pipeline');
const { renderRoute } = await import('@/test/renderRoute');

const STAGE_ORDER: readonly PipelineStage[] = [
  'CAPTACAO',
  'ESTRUTURACAO',
  'PRODUTO',
  'PROPOSTA',
  'ACOMPANHAMENTO',
];

const DEMAND_ID = '33333333-3333-4333-8333-333333333333';

function createCard(partial: Partial<PipelineCardRead> = {}): PipelineCardRead {
  return {
    id: DEMAND_ID,
    title: 'Treinamento de NR-12',
    status: 'ABERTA',
    client: { id: '11111111-1111-4111-8111-111111111111', name: 'Industria Alfa' },
    owner: { id: '22222222-2222-4222-8222-222222222222', name: 'Marina Prado' },
    created_at: '2026-09-20T09:00:00-03:00',
    updated_at: '2026-10-01T09:00:00-03:00',
    ...partial,
  };
}

/** Quadro com um cartao so, na primeira etapa: o foco aqui e o cartao. */
function withCard(card: PipelineCardRead) {
  const board: PipelineBoard = {
    stages: STAGE_ORDER.map((stage) => ({
      stage,
      total: stage === 'CAPTACAO' ? 1 : 0,
      items: stage === 'CAPTACAO' ? [card] : [],
    })),
    total: 1,
  };

  vi.mocked(getPipelineBoard).mockResolvedValue(board);
}

/** O cartao e o proprio link; o titulo da demanda o identifica. */
function findCard(): Promise<HTMLElement> {
  return screen.findByRole('link', { name: /Treinamento de NR-12/ });
}

beforeEach(() => {
  vi.clearAllMocks();
  withCard(createCard());
});

describe('cartao da demanda no pipeline', () => {
  it('diz cliente, titulo, responsavel e situacao em um cartao so', async () => {
    withCard(createCard({ status: 'GANHA' }));
    renderRoute('/pipeline');

    const card = await findCard();

    expect(within(card).getByText('Industria Alfa')).toBeDefined();
    expect(within(card).getByText('Treinamento de NR-12')).toBeDefined();
    expect(within(card).getByText('Marina Prado')).toBeDefined();
    expect(within(card).getByText('Ganha')).toBeDefined();
  });

  it('e clicavel no cartao inteiro e leva ao detalhe da demanda', async () => {
    const user = userEvent.setup();
    renderRoute('/pipeline');

    const card = await findCard();

    expect(card.getAttribute('href')).toBe(`/demandas/${DEMAND_ID}`);

    await user.click(card);

    expect(screen.getByRole('heading', { level: 1, name: 'Detalhe da demanda' })).toBeDefined();
  });

  it('distingue a demanda que exige atencao por texto, nao so por cor', async () => {
    withCard(createCard({ owner: null }));
    renderRoute('/pipeline');

    const card = await findCard();

    // O texto e o portador do aviso; cor e borda apenas o reforcam.
    expect(within(card).getByText('Sem responsavel definido')).toBeDefined();
    expect(card.className).toContain('pipeline-card--attention');
  });

  it('nao repete o marcador de forma para quem usa leitor de tela', async () => {
    withCard(createCard({ owner: null }));
    renderRoute('/pipeline');

    const card = await findCard();
    const mark = card.querySelector('.pipeline-card__attention-mark');

    // O "!" e decoracao visual: o aviso ja esta escrito ao lado dele.
    expect(mark?.getAttribute('aria-hidden')).toBe('true');
  });

  it('nao marca atencao na demanda que tem responsavel', async () => {
    renderRoute('/pipeline');

    const card = await findCard();

    expect(within(card).queryByText('Sem responsavel definido')).toBeNull();
    expect(card.className).not.toContain('pipeline-card--attention');
  });
});
