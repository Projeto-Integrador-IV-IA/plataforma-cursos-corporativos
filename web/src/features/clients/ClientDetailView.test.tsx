/**
 * Criterios de aceite da tela de detalhe e edicao do cliente (RF01; RF01.2 no
 * Documento Consolidado v1.0).
 *
 * Os testes falam com a tela pelo que o operador ve - bloco, rotulo, botao - e
 * dublam a fronteira de rede (`services/`), nao o `fetch`.
 *
 * `services/clients` e dublado por um servidor de mentira com estado: o PATCH
 * grava e o GET seguinte le o que foi gravado. Sem isso, a revalidacao que vem
 * depois de salvar devolveria o valor antigo e o teste de "edicao refletida"
 * passaria a medir o duble, nao a tela.
 */

import { screen, waitFor } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { beforeEach, describe, expect, it, vi } from 'vitest';

import { ApiError } from '@/services/api';
import type { Client, ClientUpdate, DemandRead, Page, Uuid } from '@/types/api';

vi.mock('@/services/clients', () => ({
  listClients: vi.fn(),
  getClient: vi.fn(),
  createClient: vi.fn(),
  updateClient: vi.fn(),
}));

vi.mock('@/services/demands', () => ({
  createDemand: vi.fn(),
  listDemands: vi.fn(),
  getDemand: vi.fn(),
  updateDemand: vi.fn(),
}));

const { getClient, updateClient } = await import('@/services/clients');
const { listDemands } = await import('@/services/demands');
const { renderRoute } = await import('@/test/renderRoute');

const CLIENTE: Client = {
  id: '11111111-1111-4111-8111-111111111111',
  name: 'Industria Alfa',
  cnpj: '12.345.678/0001-90',
  segment: 'Metalurgia',
  contact_name: 'Marina Prado',
  contact_email: 'marina@alfa.example',
  contact_phone: null,
  notes: 'Conta trazida pela indicacao da Beta.',
  active: true,
  created_at: '2026-09-17T09:00:00-03:00',
  updated_at: '2026-09-19T09:30:00-03:00',
};

const DEMANDA: DemandRead = {
  id: '22222222-2222-4222-8222-222222222222',
  client_id: CLIENTE.id,
  title: 'Treinamento de NR-12',
  description: 'Vinte e cinco tecnicos da planta 2.',
  owner_id: null,
  status: 'ABERTA',
  current_stage: 'CAPTACAO',
  active: true,
  created_at: '2026-09-17T09:00:00-03:00',
  updated_at: '2026-09-19T09:30:00-03:00',
};

function pagina(items: readonly DemandRead[], total = items.length): Page<DemandRead> {
  return { items, total, page: 1, size: 10 };
}

/** Estado do servidor de mentira; cada teste comeca do mesmo ponto. */
let persistido: Client = CLIENTE;

beforeEach(() => {
  vi.clearAllMocks();
  persistido = CLIENTE;
  vi.mocked(getClient).mockImplementation(() => Promise.resolve(persistido));
  vi.mocked(updateClient).mockImplementation((_clientId: Uuid, payload: ClientUpdate) => {
    persistido = { ...persistido, ...payload };

    return Promise.resolve(persistido);
  });
  vi.mocked(listDemands).mockResolvedValue(pagina([DEMANDA]));
});

async function abrirDetalhe() {
  const usuario = userEvent.setup();
  renderRoute(`/clientes/${CLIENTE.id}`);
  await screen.findByRole('heading', { level: 2, name: 'Dados cadastrais' });

  return usuario;
}

/** Texto visivel na tela inteira, para conferir a presenca de um dado. */
function textoDaTela(): string {
  return document.body.textContent ?? '';
}

describe('detalhe do cliente', () => {
  it('mostra o cadastro carregado pelo identificador da rota', async () => {
    await abrirDetalhe();

    expect(getClient).toHaveBeenCalledTimes(1);
    expect(vi.mocked(getClient).mock.calls[0]?.[0]).toBe(CLIENTE.id);

    const texto = textoDaTela();
    expect(texto).toContain('Industria Alfa');
    expect(texto).toContain('12.345.678/0001-90');
    expect(texto).toContain('Metalurgia');
    expect(texto).toContain('Marina Prado');
    expect(texto).toContain('marina@alfa.example');
    expect(texto).toContain('Conta trazida pela indicacao da Beta.');
    // Campo opcional vazio aparece como ausencia, nao como espaco em branco.
    expect(texto).toContain('Nao informado');
  });

  it('nao oferece ativacao nem inativacao, que pertencem a outro requisito', async () => {
    await abrirDetalhe();

    expect(screen.queryByRole('checkbox')).toBeNull();
    expect(screen.queryByRole('button', { name: /Inativar/ })).toBeNull();
    expect(textoDaTela()).toContain('Inativar o cliente ainda nao e possivel por esta tela');
  });
});

describe('edicao do cadastro do cliente', () => {
  it('salva o que foi alterado e reflete na consulta seguinte', async () => {
    const usuario = await abrirDetalhe();

    await usuario.click(screen.getByRole('button', { name: 'Editar cadastro' }));

    const razaoSocial = screen.getByRole('textbox', { name: /Razao social/ });
    await usuario.clear(razaoSocial);
    await usuario.type(razaoSocial, 'Industria Alfa S.A.');
    await usuario.click(screen.getByRole('button', { name: 'Salvar cadastro' }));

    await waitFor(() => expect(updateClient).toHaveBeenCalledTimes(1));
    // So o campo alterado vai no corpo: o PATCH altera somente o que recebe.
    expect(updateClient).toHaveBeenCalledWith(CLIENTE.id, { name: 'Industria Alfa S.A.' });

    expect(await screen.findByText('Cadastro do cliente salvo.')).toBeDefined();
    await waitFor(() => expect(textoDaTela()).toContain('Industria Alfa S.A.'));
    expect(screen.getByRole('button', { name: 'Editar cadastro' })).toBeDefined();
  });

  it('envia os demais campos alterados de uma vez', async () => {
    const usuario = await abrirDetalhe();

    await usuario.click(screen.getByRole('button', { name: 'Editar cadastro' }));
    await usuario.type(screen.getByRole('textbox', { name: 'Segmento' }), ' pesada');
    await usuario.type(screen.getByRole('textbox', { name: 'Telefone do contato' }), '11999990000');
    await usuario.click(screen.getByRole('button', { name: 'Salvar cadastro' }));

    await waitFor(() => expect(updateClient).toHaveBeenCalledTimes(1));
    expect(updateClient).toHaveBeenCalledWith(CLIENTE.id, {
      segment: 'Metalurgia pesada',
      contact_phone: '11999990000',
    });
  });

  it('limpa o campo opcional esvaziado, enviando ausencia declarada', async () => {
    const usuario = await abrirDetalhe();

    await usuario.click(screen.getByRole('button', { name: 'Editar cadastro' }));
    await usuario.clear(screen.getByRole('textbox', { name: 'Observacoes' }));
    await usuario.click(screen.getByRole('button', { name: 'Salvar cadastro' }));

    await waitFor(() => expect(updateClient).toHaveBeenCalledTimes(1));
    expect(updateClient).toHaveBeenCalledWith(CLIENTE.id, { notes: null });
  });

  it('nao salva enquanto a razao social estiver vazia', async () => {
    const usuario = await abrirDetalhe();

    await usuario.click(screen.getByRole('button', { name: 'Editar cadastro' }));
    await usuario.clear(screen.getByRole('textbox', { name: /Razao social/ }));

    const botao = screen.getByRole<HTMLButtonElement>('button', { name: 'Salvar cadastro' });
    expect(botao.disabled).toBe(true);
    expect(textoDaTela()).toContain('A razao social identifica a empresa e nao pode ficar vazia.');

    await usuario.click(botao);
    expect(updateClient).not.toHaveBeenCalled();
  });

  it('nao envia nada quando o operador nao mudou campo nenhum', async () => {
    const usuario = await abrirDetalhe();

    await usuario.click(screen.getByRole('button', { name: 'Editar cadastro' }));

    expect(
      screen.getByRole<HTMLButtonElement>('button', { name: 'Salvar cadastro' }).disabled,
    ).toBe(true);
    expect(updateClient).not.toHaveBeenCalled();
  });

  it('mostra a mensagem da API quando a edicao falha e mantem o formulario aberto', async () => {
    vi.mocked(updateClient).mockRejectedValue(
      new ApiError({
        kind: 'http',
        code: 'CLIENT_CNPJ_CONFLICT',
        message: 'CNPJ ja cadastrado para outra empresa.',
        status: 409,
      }),
    );
    const usuario = await abrirDetalhe();

    await usuario.click(screen.getByRole('button', { name: 'Editar cadastro' }));
    await usuario.type(screen.getByRole('textbox', { name: 'Nome do contato' }), ' Junior');
    await usuario.click(screen.getByRole('button', { name: 'Salvar cadastro' }));

    expect(await screen.findByText('CNPJ ja cadastrado para outra empresa.')).toBeDefined();
    expect(screen.getByRole('button', { name: 'Salvar cadastro' })).toBeDefined();
  });
});

describe('demandas do cliente', () => {
  it('lista as demandas filtradas por cliente, com link para cada uma', async () => {
    await abrirDetalhe();

    await screen.findByRole('link', { name: DEMANDA.title });
    expect(listDemands).toHaveBeenCalledWith(
      { client_id: CLIENTE.id, limit: 10 },
      expect.anything(),
    );
    expect(screen.getByRole('link', { name: DEMANDA.title }).getAttribute('href')).toBe(
      `/demandas/${DEMANDA.id}`,
    );
    expect(textoDaTela()).toContain('Captacao');
    expect(textoDaTela()).toContain('Aberta');
  });

  it('leva a listagem de demandas ja filtrada por este cliente', async () => {
    await abrirDetalhe();

    const link = await screen.findByRole('link', { name: /Ver as demandas deste cliente/ });
    expect(link.getAttribute('href')).toBe(`/demandas?cliente=${CLIENTE.id}`);
  });

  it('avisa quando o cliente ainda nao tem demanda', async () => {
    vi.mocked(listDemands).mockResolvedValue(pagina([]));
    await abrirDetalhe();

    expect(await screen.findByText('Este cliente ainda nao tem demanda aberta.')).toBeDefined();
    expect(screen.queryByRole('link', { name: DEMANDA.title })).toBeNull();
  });

  it('explica a falha das demandas sem derrubar o cadastro', async () => {
    vi.mocked(listDemands).mockRejectedValue(
      new ApiError({
        kind: 'network',
        code: 'NETWORK_ERROR',
        message: 'Nao foi possivel falar com o servidor. Verifique sua conexao.',
      }),
    );
    await abrirDetalhe();

    expect(
      await screen.findByText(
        'Nao foi possivel falar com o servidor. Verifique sua conexao.',
        {},
        { timeout: 4000 },
      ),
    ).toBeDefined();
    expect(textoDaTela()).toContain('Industria Alfa');
  });
});

describe('cliente inexistente', () => {
  it('mostra estado de vazio tratado, com o caminho de volta', async () => {
    vi.mocked(getClient).mockRejectedValue(
      new ApiError({
        kind: 'http',
        code: 'CLIENT_NOT_FOUND',
        message: 'Cliente inexistente.',
        status: 404,
      }),
    );
    renderRoute(`/clientes/${CLIENTE.id}`);

    expect(
      await screen.findByText(
        'Nenhum cliente cadastrado com este identificador.',
        {},
        { timeout: 4000 },
      ),
    ).toBeDefined();
    expect(screen.queryByRole('heading', { level: 2, name: 'Dados cadastrais' })).toBeNull();
    // O cabecalho da tela continua de pe: o operador sabe onde esta.
    expect(screen.getByRole('heading', { level: 1, name: 'Detalhe do cliente' })).toBeDefined();
    expect(
      screen.getAllByRole('link', { name: 'Voltar para a lista de clientes' }).length,
    ).toBeGreaterThan(0);
  });

  it('mostra a mensagem da API quando a falha nao e de identificador', async () => {
    vi.mocked(getClient).mockRejectedValue(
      new ApiError({
        kind: 'timeout',
        code: 'REQUEST_TIMEOUT',
        message: 'O servico demorou mais que o esperado para responder. Tente novamente.',
      }),
    );
    renderRoute(`/clientes/${CLIENTE.id}`);

    expect(
      await screen.findByText(
        'O servico demorou mais que o esperado para responder. Tente novamente.',
        {},
        { timeout: 4000 },
      ),
    ).toBeDefined();
  });
});
