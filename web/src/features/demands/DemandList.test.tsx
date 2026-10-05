/**
 * Criterios de aceite da listagem de demandas (RF03).
 *
 * Os testes falam com a tela pelo que o operador ve - linha da tabela, rotulo
 * do filtro, botao do paginador - e dublam a fronteira de rede (`services/`),
 * nao o `fetch`: e ali que mora o contrato desta tela.
 *
 * A ordenacao e do servidor (`created_at DESC, id DESC`), entao o que se
 * verifica aqui e que a listagem nao a embaralha: a pagina 2 comeca onde a 1
 * parou.
 */

import { screen, waitFor, within } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { beforeEach, describe, expect, it, vi } from 'vitest';

import { ApiError } from '@/services/api';
import type { Client, DemandRead, DemandListParams, Page } from '@/types/api';

vi.mock('@/services/clients', () => ({ listClients: vi.fn() }));
vi.mock('@/services/demands', () => ({ listDemands: vi.fn() }));

const { listClients } = await import('@/services/clients');
const { listDemands } = await import('@/services/demands');
const { renderRoute } = await import('@/test/renderRoute');

const ALFA: Client = {
  id: '11111111-1111-4111-8111-111111111111',
  name: 'Industria Alfa',
  cnpj: '12.345.678/0001-90',
  segment: 'Metalurgia',
  contact_name: 'Marina',
  contact_email: 'marina@alfa.example',
  contact_phone: null,
  notes: null,
  active: true,
  created_at: '2026-09-01T10:00:00-03:00',
  updated_at: '2026-09-01T10:00:00-03:00',
};

const BETA: Client = { ...ALFA, id: '22222222-2222-4222-8222-222222222222', name: 'Comercio Beta' };

const TOTAL_DE_DEMANDAS = 25;
const TAMANHO_DA_PAGINA = 20;

function criarDemanda(numero: number, parcial: Partial<DemandRead> = {}): DemandRead {
  const rotulo = String(numero).padStart(2, '0');

  return {
    id: `demanda-${rotulo}`,
    client_id: ALFA.id,
    title: `Demanda ${rotulo}`,
    description: null,
    owner_id: null,
    status: 'ABERTA',
    current_stage: 'CAPTACAO',
    active: true,
    created_at: '2026-09-20T09:00:00-03:00',
    updated_at: '2026-09-20T09:00:00-03:00',
    ...parcial,
  };
}

/** Recorte do servidor: itens ja ordenados, `total` contado antes do corte. */
function paginaDe(offset: number): Page<DemandRead> {
  const items = Array.from({ length: TOTAL_DE_DEMANDAS }, (_, indice) => criarDemanda(indice + 1))
    .slice(offset, offset + TAMANHO_DA_PAGINA);

  return {
    items,
    total: TOTAL_DE_DEMANDAS,
    page: Math.floor(offset / TAMANHO_DA_PAGINA) + 1,
    size: TAMANHO_DA_PAGINA,
  };
}

function comPagina(itens: readonly DemandRead[], total = itens.length) {
  vi.mocked(listDemands).mockResolvedValue({ items: itens, total, page: 1, size: TAMANHO_DA_PAGINA });
}

function ultimosFiltros(): DemandListParams {
  const chamadas = vi.mocked(listDemands).mock.calls;
  const ultima = chamadas[chamadas.length - 1];

  return ultima?.[0] ?? {};
}

function linhasDeDados(): readonly HTMLElement[] {
  // A primeira linha e o cabecalho; as demais sao as demandas, na ordem
  // devolvida pelo servidor.
  return screen.getAllByRole('row').slice(1);
}

beforeEach(() => {
  vi.clearAllMocks();
  vi.mocked(listClients).mockResolvedValue({
    items: [ALFA, BETA],
    total: 2,
    page: 1,
    size: 100,
  });
  vi.mocked(listDemands).mockImplementation((params: DemandListParams = {}) =>
    Promise.resolve(paginaDe(params.offset ?? 0)),
  );
});

describe('listagem de demandas', () => {
  it('mostra cliente, titulo, etapa corrente, responsavel e situacao de cada demanda', async () => {
    comPagina([
      criarDemanda(1, {
        title: 'Treinamento de NR-12',
        client_id: BETA.id,
        current_stage: 'ESTRUTURACAO',
        status: 'GANHA',
        owner_id: 'aabbccdd-1111-4111-8111-111111111111',
      }),
    ]);
    renderRoute('/demandas');

    const linha = await screen.findByRole('row', { name: /Treinamento de NR-12/ });

    expect(linha.textContent).toContain('Comercio Beta');
    expect(linha.textContent).toContain('Estruturacao');
    expect(linha.textContent).toContain('Ganha');
    expect(linha.textContent).toContain('aabbccdd');
    expect(within(linha).getByRole('link', { name: 'Treinamento de NR-12' })).toBeDefined();
  });

  it('associa cada coluna ao seu cabecalho e usa o titulo como cabecalho da linha', async () => {
    renderRoute('/demandas');
    await screen.findByRole('row', { name: /Demanda 01/ });

    for (const coluna of ['Demanda', 'Cliente', 'Etapa corrente', 'Situacao', 'Responsavel']) {
      expect(screen.getByRole('columnheader', { name: coluna })).toBeDefined();
    }
    expect(screen.getByRole('rowheader', { name: 'Demanda 01' })).toBeDefined();
  });

  it('diz "nao atribuido" quando a demanda esta sem responsavel', async () => {
    comPagina([criarDemanda(1, { owner_id: null })]);
    renderRoute('/demandas');

    const linha = await screen.findByRole('row', { name: /Demanda 01/ });

    expect(linha.textContent).toContain('Nao atribuido');
  });

  it('avanca de pagina retomando a ordem do servidor onde a anterior parou', async () => {
    const usuario = userEvent.setup();
    renderRoute('/demandas');
    await screen.findByRole('row', { name: /Demanda 01/ });

    await usuario.click(screen.getByRole('button', { name: 'Proxima pagina' }));

    await waitFor(() => expect(ultimosFiltros().offset).toBe(TAMANHO_DA_PAGINA));
    expect(ultimosFiltros().limit).toBe(TAMANHO_DA_PAGINA);
    await screen.findByRole('row', { name: /Demanda 21/ });
    expect(linhasDeDados()[0]?.textContent).toContain('Demanda 21');
    expect(screen.queryByRole('row', { name: /Demanda 01/ })).toBeNull();
  });

  it('retoma pagina e filtro vindos da URL, sem pedir tudo de novo', async () => {
    renderRoute('/demandas?pagina=2&situacao=GANHA');
    await screen.findByRole('row', { name: /Demanda 21/ });

    expect(ultimosFiltros().offset).toBe(TAMANHO_DA_PAGINA);
    expect(ultimosFiltros().status).toBe('GANHA');
    expect(screen.getByLabelText<HTMLSelectElement>('Situacao').value).toBe('GANHA');
  });

  it('ignora pagina invalida na URL em vez de pedir um recorte negativo', async () => {
    renderRoute('/demandas?pagina=-3');
    await screen.findByRole('row', { name: /Demanda 01/ });

    expect(ultimosFiltros().offset).toBe(0);
  });

  it('volta para a primeira pagina ao trocar o filtro de situacao', async () => {
    const usuario = userEvent.setup();
    renderRoute('/demandas?pagina=2');
    await screen.findByRole('row', { name: /Demanda 21/ });

    await usuario.selectOptions(screen.getByLabelText('Situacao'), 'PERDIDA');

    await waitFor(() => expect(ultimosFiltros().status).toBe('PERDIDA'));
    expect(ultimosFiltros().offset).toBe(0);
  });

  it('filtra por cliente usando a lista de clientes carregada', async () => {
    const usuario = userEvent.setup();
    renderRoute('/demandas');
    await screen.findByRole('row', { name: /Demanda 01/ });

    await usuario.selectOptions(screen.getByLabelText('Cliente'), BETA.id);

    await waitFor(() => expect(ultimosFiltros().client_id).toBe(BETA.id));
    expect(ultimosFiltros().offset).toBe(0);
  });

  it('trata lista vazia sem filtro convidando a abrir a primeira demanda', async () => {
    comPagina([], 0);
    renderRoute('/demandas');

    expect(await screen.findByText(/Nenhuma demanda aberta ate agora/)).toBeDefined();
    expect(screen.queryByRole('table')).toBeNull();
    expect(screen.getByRole('link', { name: 'Abra a primeira negociacao' })).toBeDefined();
  });

  it('trata lista vazia com filtro oferecendo limpar o recorte', async () => {
    const usuario = userEvent.setup();
    comPagina([], 0);
    renderRoute('/demandas?situacao=CANCELADA');

    expect(await screen.findByText(/Nenhuma demanda atende a este filtro/)).toBeDefined();

    await usuario.click(screen.getByRole('button', { name: 'Limpar filtros' }));

    await waitFor(() => expect(ultimosFiltros().status).toBeUndefined());
  });

  it('mostra a mensagem da API quando a listagem falha, com opcao de repetir', async () => {
    vi.mocked(listDemands).mockRejectedValue(
      new ApiError({
        kind: 'http',
        code: 'INVALID_FILTER',
        message: 'Periodo informado e invalido.',
        status: 422,
      }),
    );
    renderRoute('/demandas');

    // A regiao global de mensagens ja ocupa um `role="alert"` vazio, entao a
    // busca parte do texto e confirma que ele esta dentro de um aviso assertivo.
    const aviso = await screen.findByText('Periodo informado e invalido.', {}, { timeout: 3000 });

    expect(aviso.closest('[role="alert"]')).not.toBeNull();
    expect(screen.getByRole('button', { name: 'Tentar novamente' })).toBeDefined();
  });

  it('continua listando quando os nomes de cliente nao carregam', async () => {
    vi.mocked(listClients).mockRejectedValue(
      new ApiError({
        kind: 'network',
        code: 'NETWORK_ERROR',
        message: 'Nao foi possivel falar com o servidor.',
      }),
    );
    renderRoute('/demandas');

    const linha = await screen.findByRole('row', { name: /Demanda 01/ });

    expect(linha.textContent).toContain(ALFA.id.slice(0, 8));
    expect(
      await screen.findByText(/identificador do cliente no lugar do nome/, {}, { timeout: 3000 }),
    ).toBeDefined();
    expect(screen.getByLabelText<HTMLSelectElement>('Cliente').disabled).toBe(true);
  });

  it('preserva o acesso a abertura de nova demanda', async () => {
    renderRoute('/demandas');
    await screen.findByRole('row', { name: /Demanda 01/ });

    expect(screen.getByRole('link', { name: 'Abrir nova demanda' })).toBeDefined();
  });
});
