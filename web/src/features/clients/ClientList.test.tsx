/**
 * Criterios de aceite da listagem de clientes (RF03).
 *
 * Os testes falam com a tela pelo que o operador ve - linha da tabela, botao do
 * paginador, texto do estado vazio - e dublam a fronteira de rede
 * (`services/clients`), nao o `fetch`: e ali que mora o contrato desta tela.
 *
 * A ordenacao e do servidor (`created_at DESC, id ASC`) e o contrato nao a
 * parametriza, entao o que se verifica aqui e que a listagem nao a embaralha: a
 * pagina 2 comeca onde a 1 parou, e a pagina pedida ao servico e a que esta na
 * URL.
 */

import { screen, waitFor, within } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { beforeEach, describe, expect, it, vi } from 'vitest';

import { ApiError } from '@/services/api';
import type { Client, ClientListParams, Page } from '@/types/api';

vi.mock('@/services/clients', () => ({ listClients: vi.fn() }));

const { listClients } = await import('@/services/clients');
const { renderRoute } = await import('@/test/renderRoute');

const TOTAL_DE_CLIENTES = 25;
const TAMANHO_DA_PAGINA = 20;

function criarCliente(numero: number, parcial: Partial<Client> = {}): Client {
  const rotulo = String(numero).padStart(2, '0');

  return {
    id: `cliente-${rotulo}`,
    name: `Cliente ${rotulo}`,
    cnpj: null,
    segment: null,
    contact_name: null,
    contact_email: null,
    contact_phone: null,
    notes: null,
    active: true,
    created_at: '2026-09-01T10:00:00-03:00',
    updated_at: '2026-09-01T10:00:00-03:00',
    ...parcial,
  };
}

/** Recorte do servidor: itens ja ordenados, `total` contado antes do corte. */
function paginaDe(page: number): Page<Client> {
  const offset = (page - 1) * TAMANHO_DA_PAGINA;
  const items = Array.from({ length: TOTAL_DE_CLIENTES }, (_, indice) =>
    criarCliente(indice + 1),
  ).slice(offset, offset + TAMANHO_DA_PAGINA);

  return { items, total: TOTAL_DE_CLIENTES, page, size: TAMANHO_DA_PAGINA };
}

function comPagina(itens: readonly Client[], total = itens.length) {
  vi.mocked(listClients).mockResolvedValue({
    items: itens,
    total,
    page: 1,
    size: TAMANHO_DA_PAGINA,
  });
}

function ultimosParametros(): ClientListParams {
  const chamadas = vi.mocked(listClients).mock.calls;
  const ultima = chamadas[chamadas.length - 1];

  return ultima?.[0] ?? {};
}

function linhasDeDados(): readonly HTMLElement[] {
  // A primeira linha e o cabecalho; as demais sao os clientes, na ordem
  // devolvida pelo servidor.
  return screen.getAllByRole('row').slice(1);
}

beforeEach(() => {
  vi.clearAllMocks();
  vi.mocked(listClients).mockImplementation((params: ClientListParams = {}) =>
    Promise.resolve(paginaDe(params.page ?? 1)),
  );
});

describe('listagem de clientes', () => {
  it('mostra nome, CNPJ, segmento, contato e situacao de cada cliente', async () => {
    comPagina([
      criarCliente(1, {
        name: 'Industria Alfa',
        cnpj: '12.345.678/0001-90',
        segment: 'Metalurgia',
        contact_name: 'Marina Prado',
      }),
    ]);
    renderRoute('/clientes');

    const linha = await screen.findByRole('row', { name: /Industria Alfa/ });

    expect(linha.textContent).toContain('12.345.678/0001-90');
    expect(linha.textContent).toContain('Metalurgia');
    expect(linha.textContent).toContain('Marina Prado');
    expect(linha.textContent).toContain('Ativo');
    expect(within(linha).getByRole('link', { name: 'Industria Alfa' })).toBeDefined();
  });

  it('associa cada coluna ao seu cabecalho e usa o nome como cabecalho da linha', async () => {
    renderRoute('/clientes');
    await screen.findByRole('row', { name: /Cliente 01/ });

    for (const coluna of ['Cliente', 'CNPJ', 'Segmento', 'Contato', 'Situacao', 'Cadastrado em']) {
      expect(screen.getByRole('columnheader', { name: coluna })).toBeDefined();
    }
    expect(screen.getByRole('rowheader', { name: 'Cliente 01' })).toBeDefined();
  });

  it('diz "nao informado" no lugar de celula vazia quando o cadastro so tem nome', async () => {
    comPagina([criarCliente(1, { cnpj: null, segment: null, contact_name: null })]);
    renderRoute('/clientes');

    const linha = await screen.findByRole('row', { name: /Cliente 01/ });

    expect(within(linha).getAllByText('Nao informado')).toHaveLength(3);
  });

  it('distingue o cliente inativo do ativo', async () => {
    comPagina([criarCliente(1, { active: false })]);
    renderRoute('/clientes');

    const linha = await screen.findByRole('row', { name: /Cliente 01/ });

    expect(linha.textContent).toContain('Inativo');
  });

  it('avanca de pagina retomando a ordem do servidor onde a anterior parou', async () => {
    const usuario = userEvent.setup();
    renderRoute('/clientes');
    await screen.findByRole('row', { name: /Cliente 01/ });

    await usuario.click(screen.getByRole('button', { name: 'Proxima pagina' }));

    await waitFor(() => expect(ultimosParametros().page).toBe(2));
    expect(ultimosParametros().size).toBe(TAMANHO_DA_PAGINA);
    await screen.findByRole('row', { name: /Cliente 21/ });
    expect(linhasDeDados()[0]?.textContent).toContain('Cliente 21');
    expect(screen.queryByRole('row', { name: /Cliente 01/ })).toBeNull();
  });

  it('retoma a pagina vinda da URL, para o estado sobreviver ao recarregar', async () => {
    renderRoute('/clientes?pagina=2');

    await screen.findByRole('row', { name: /Cliente 21/ });
    expect(ultimosParametros().page).toBe(2);
    expect(screen.getByText(/Pagina 2 de 2/)).toBeDefined();
  });

  it('ignora pagina invalida na URL em vez de pedir um recorte negativo', async () => {
    renderRoute('/clientes?pagina=-3');

    await screen.findByRole('row', { name: /Cliente 01/ });
    expect(ultimosParametros().page).toBe(1);
  });

  it('trata lista vazia convidando ao primeiro cadastro', async () => {
    comPagina([], 0);
    renderRoute('/clientes');

    expect(await screen.findByText(/Nenhum cliente cadastrado ate agora/)).toBeDefined();
    expect(screen.queryByRole('table')).toBeNull();
    expect(screen.getByRole('link', { name: 'Cadastre o primeiro cliente' })).toBeDefined();
  });

  it('oferece a volta quando a URL aponta para uma pagina alem do fim', async () => {
    const usuario = userEvent.setup();
    vi.mocked(listClients).mockResolvedValue({
      items: [],
      total: TOTAL_DE_CLIENTES,
      page: 9,
      size: TAMANHO_DA_PAGINA,
    });
    renderRoute('/clientes?pagina=9');

    expect(await screen.findByText('Esta pagina nao tem clientes.')).toBeDefined();
    expect(screen.queryByText(/Nenhum cliente cadastrado ate agora/)).toBeNull();

    vi.mocked(listClients).mockImplementation((params: ClientListParams = {}) =>
      Promise.resolve(paginaDe(params.page ?? 1)),
    );
    await usuario.click(screen.getByRole('button', { name: 'Voltar para a primeira pagina' }));

    await waitFor(() => expect(ultimosParametros().page).toBe(1));
    expect(await screen.findByRole('row', { name: /Cliente 01/ })).toBeDefined();
  });

  it('mostra a mensagem da API quando a listagem falha, com opcao de repetir', async () => {
    vi.mocked(listClients).mockRejectedValue(
      new ApiError({
        kind: 'http',
        code: 'INVALID_PAGINATION',
        message: 'Paginacao informada e invalida.',
        status: 422,
      }),
    );
    renderRoute('/clientes');

    // A regiao global de mensagens ja ocupa o unico `role="alert"` da tela,
    // entao o aviso local se anuncia por `aria-live`: a busca parte do texto e
    // confirma que ele esta dentro de uma regiao assertiva.
    const aviso = await screen.findByText('Paginacao informada e invalida.', {}, { timeout: 3000 });

    expect(aviso.closest('[aria-live="assertive"]')).not.toBeNull();
    expect(screen.getByRole('button', { name: 'Tentar novamente' })).toBeDefined();
  });

  it('preserva o acesso ao cadastro de cliente', async () => {
    renderRoute('/clientes');
    await screen.findByRole('row', { name: /Cliente 01/ });

    expect(screen.getByRole('link', { name: 'Cadastrar cliente' })).toBeDefined();
  });
});
