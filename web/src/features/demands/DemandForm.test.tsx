/**
 * Criterios de aceite do formulario de criacao de demanda (RF02).
 *
 * Os testes falam com o formulario pelo que o operador ve - rotulo, opcao,
 * botao - e dublam a fronteira de rede (`services/`), nao o `fetch`: e ali que
 * mora o contrato desta tela.
 */

import { screen, waitFor } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import type * as ReactRouter from 'react-router-dom';
import { beforeEach, describe, expect, it, vi } from 'vitest';

import { ApiError } from '@/services/api';
import type { Client, DemandRead } from '@/types/api';

const navegou = vi.fn();

vi.mock('react-router-dom', async () => {
  const real = await vi.importActual<typeof ReactRouter>('react-router-dom');
  return { ...real, useNavigate: () => navegou };
});

vi.mock('@/services/clients', () => ({ listClients: vi.fn() }));
vi.mock('@/services/demands', () => ({ createDemand: vi.fn() }));

const { listClients } = await import('@/services/clients');
const { createDemand } = await import('@/services/demands');
const { renderRoute } = await import('@/test/renderRoute');

const CLIENTE: Client = {
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

const DEMANDA: DemandRead = {
  id: '22222222-2222-4222-8222-222222222222',
  client_id: CLIENTE.id,
  title: 'Treinamento de NR-12',
  description: 'Vinte e cinco tecnicos da planta 2.',
  owner_id: null,
  status: 'ABERTA',
  current_stage: 'CAPTACAO',
  active: true,
  created_at: '2026-09-21T09:00:00-03:00',
  updated_at: '2026-09-21T09:00:00-03:00',
};

function comClientes(itens: readonly Client[]) {
  vi.mocked(listClients).mockResolvedValue({ items: itens, total: itens.length, page: 1, size: 100 });
}

beforeEach(() => {
  vi.clearAllMocks();
  comClientes([CLIENTE]);
  vi.mocked(createDemand).mockResolvedValue(DEMANDA);
});

async function abrirFormulario() {
  const usuario = userEvent.setup();
  renderRoute('/demandas/nova');
  await screen.findByRole('option', { name: /Industria Alfa/ });
  return usuario;
}

describe('formulario de criacao de demanda', () => {
  it('cria a demanda vinculada ao cliente escolhido e leva ao detalhe', async () => {
    const usuario = await abrirFormulario();

    await usuario.selectOptions(screen.getByLabelText(/Cliente/), CLIENTE.id);
    await usuario.type(screen.getByLabelText(/Titulo/), 'Treinamento de NR-12');
    await usuario.type(screen.getByLabelText(/Contexto/), 'Vinte e cinco tecnicos da planta 2.');
    await usuario.click(screen.getByRole('button', { name: 'Criar demanda' }));

    await waitFor(() => expect(createDemand).toHaveBeenCalledTimes(1));
    expect(createDemand).toHaveBeenCalledWith({
      client_id: CLIENTE.id,
      title: 'Treinamento de NR-12',
      description: 'Vinte e cinco tecnicos da planta 2.',
    });
    await waitFor(() => expect(navegou).toHaveBeenCalledWith(`/demandas/${DEMANDA.id}`));
    expect((await screen.findByRole('status')).textContent).toContain('Treinamento de NR-12');
  });

  it('nao envia enquanto nao houver cliente selecionado', async () => {
    const usuario = await abrirFormulario();

    await usuario.type(screen.getByLabelText(/Titulo/), 'Sem cliente');
    const botao = screen.getByRole<HTMLButtonElement>('button', { name: 'Criar demanda' });

    expect(botao.disabled).toBe(true);
    await usuario.click(botao);
    expect(createDemand).not.toHaveBeenCalled();
  });

  it('nao envia enquanto o titulo for so espaco em branco', async () => {
    const usuario = await abrirFormulario();

    await usuario.selectOptions(screen.getByLabelText(/Cliente/), CLIENTE.id);
    await usuario.type(screen.getByLabelText(/Titulo/), '   ');

    expect(screen.getByRole<HTMLButtonElement>('button', { name: 'Criar demanda' }).disabled).toBe(
      true,
    );
    expect(createDemand).not.toHaveBeenCalled();
  });

  it('omite o contexto quando o campo fica vazio', async () => {
    const usuario = await abrirFormulario();

    await usuario.selectOptions(screen.getByLabelText(/Cliente/), CLIENTE.id);
    await usuario.type(screen.getByLabelText(/Titulo/), 'Somente o essencial');
    await usuario.click(screen.getByRole('button', { name: 'Criar demanda' }));

    await waitFor(() => expect(createDemand).toHaveBeenCalledTimes(1));
    expect(createDemand).toHaveBeenCalledWith({
      client_id: CLIENTE.id,
      title: 'Somente o essencial',
      description: null,
    });
  });

  it('mostra a mensagem da API quando a criacao falha, e nao navega', async () => {
    vi.mocked(createDemand).mockRejectedValue(
      new ApiError({
        kind: 'http',
        code: 'CLIENT_NOT_FOUND',
        message: 'Cliente nao encontrado.',
        status: 404,
      }),
    );
    const usuario = await abrirFormulario();

    await usuario.selectOptions(screen.getByLabelText(/Cliente/), CLIENTE.id);
    await usuario.type(screen.getByLabelText(/Titulo/), 'Demanda orfa');
    await usuario.click(screen.getByRole('button', { name: 'Criar demanda' }));

    expect((await screen.findByRole('alert')).textContent).toContain('Cliente nao encontrado.');
    expect(navegou).not.toHaveBeenCalled();
  });

  it('avisa quando nao ha cliente cadastrado, em vez de oferecer selecao vazia', async () => {
    comClientes([]);
    renderRoute('/demandas/nova');

    expect(await screen.findByText(/Nenhum cliente cadastrado/, {}, { timeout: 3000 })).toBeDefined();
    expect(screen.getByRole<HTMLButtonElement>('button', { name: 'Criar demanda' }).disabled).toBe(
      true,
    );
  });

  it('explica a falha quando a lista de clientes nao carrega', async () => {
    vi.mocked(listClients).mockRejectedValue(
      new ApiError({
        kind: 'network',
        code: 'NETWORK_ERROR',
        message: 'Nao foi possivel falar com o servidor.',
      }),
    );
    renderRoute('/demandas/nova');

    expect(
      await screen.findByText(/Nao foi possivel falar com o servidor/, {}, { timeout: 3000 }),
    ).toBeDefined();
    expect(screen.getByLabelText<HTMLSelectElement>(/Cliente/).disabled).toBe(true);
  });
});
