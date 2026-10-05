/**
 * Criterios de aceite do formulario de cadastro de cliente (RF01).
 *
 * Os testes falam com o formulario pelo que o operador ve - rotulo, botao,
 * mensagem - e dublam a fronteira de rede (`services/`), nao o `fetch`: e ali
 * que mora o contrato desta tela.
 */

import { screen, waitFor } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import type * as ReactRouter from 'react-router-dom';
import { beforeEach, describe, expect, it, vi } from 'vitest';

import { ApiError } from '@/services/api';
import type { Client } from '@/types/api';

const navegou = vi.fn();

vi.mock('react-router-dom', async () => {
  const real = await vi.importActual<typeof ReactRouter>('react-router-dom');
  return { ...real, useNavigate: () => navegou };
});

vi.mock('@/services/clients', () => ({ createClient: vi.fn() }));

const { createClient } = await import('@/services/clients');
const { renderRoute } = await import('@/test/renderRoute');

const CLIENTE: Client = {
  id: '11111111-1111-4111-8111-111111111111',
  name: 'Industria Alfa',
  cnpj: '12.345.678/0001-90',
  segment: 'Metalurgia',
  contact_name: 'Marina',
  contact_email: 'marina@alfa.example',
  contact_phone: '(11) 99999-0000',
  notes: 'Conta trazida pela indicacao da Beta.',
  active: true,
  created_at: '2026-09-21T09:00:00-03:00',
  updated_at: '2026-09-21T09:00:00-03:00',
};

beforeEach(() => {
  vi.clearAllMocks();
  vi.mocked(createClient).mockResolvedValue(CLIENTE);
});

function abrirFormulario() {
  const usuario = userEvent.setup();
  renderRoute('/clientes/novo');

  return usuario;
}

function botaoDeEnvio() {
  return screen.getByRole<HTMLButtonElement>('button', { name: 'Cadastrar cliente' });
}

describe('formulario de cadastro de cliente', () => {
  it('cadastra o cliente com todos os campos e volta para a listagem', async () => {
    const usuario = abrirFormulario();

    await usuario.type(screen.getByLabelText(/Razao social/), 'Industria Alfa');
    await usuario.type(screen.getByLabelText(/CNPJ/), '12.345.678/0001-90');
    await usuario.type(screen.getByLabelText(/Segmento/), 'Metalurgia');
    await usuario.type(screen.getByLabelText(/Nome do contato/), 'Marina');
    await usuario.type(screen.getByLabelText(/E-mail do contato/), 'marina@alfa.example');
    await usuario.type(screen.getByLabelText(/Telefone do contato/), '(11) 99999-0000');
    await usuario.type(
      screen.getByLabelText(/Observacoes/),
      'Conta trazida pela indicacao da Beta.',
    );
    await usuario.click(botaoDeEnvio());

    await waitFor(() => expect(createClient).toHaveBeenCalledTimes(1));
    expect(createClient).toHaveBeenCalledWith({
      name: 'Industria Alfa',
      cnpj: '12.345.678/0001-90',
      segment: 'Metalurgia',
      contact_name: 'Marina',
      contact_email: 'marina@alfa.example',
      contact_phone: '(11) 99999-0000',
      notes: 'Conta trazida pela indicacao da Beta.',
    });
    await waitFor(() => expect(navegou).toHaveBeenCalledWith('/clientes'));
    expect((await screen.findByRole('status')).textContent).toContain('Industria Alfa');
  });

  it('envia null nos campos opcionais deixados em branco, nunca string vazia', async () => {
    const usuario = abrirFormulario();

    await usuario.type(screen.getByLabelText(/Razao social/), '  Industria Alfa  ');
    await usuario.type(screen.getByLabelText(/Observacoes/), '   ');
    await usuario.click(botaoDeEnvio());

    await waitFor(() => expect(createClient).toHaveBeenCalledTimes(1));
    expect(createClient).toHaveBeenCalledWith({
      name: 'Industria Alfa',
      cnpj: null,
      segment: null,
      contact_name: null,
      contact_email: null,
      contact_phone: null,
      notes: null,
    });
  });

  it('nao envia enquanto a razao social estiver vazia', async () => {
    abrirFormulario();

    expect(botaoDeEnvio().disabled).toBe(true);
  });

  it('nao envia enquanto a razao social for so espaco em branco', async () => {
    const usuario = abrirFormulario();

    await usuario.type(screen.getByLabelText(/Razao social/), '   ');

    const botao = botaoDeEnvio();
    expect(botao.disabled).toBe(true);
    await usuario.click(botao);
    expect(createClient).not.toHaveBeenCalled();
  });

  it('mostra a mensagem da API quando o cadastro falha, e nao navega', async () => {
    vi.mocked(createClient).mockRejectedValue(
      new ApiError({
        kind: 'http',
        code: 'CLIENT_CNPJ_ALREADY_EXISTS',
        message: 'Ja existe cliente com este CNPJ.',
        status: 409,
      }),
    );
    const usuario = abrirFormulario();

    await usuario.type(screen.getByLabelText(/Razao social/), 'Industria Alfa');
    await usuario.type(screen.getByLabelText(/CNPJ/), '12.345.678/0001-90');
    await usuario.click(botaoDeEnvio());

    expect((await screen.findByRole('alert')).textContent).toContain(
      'Ja existe cliente com este CNPJ.',
    );
    expect(navegou).not.toHaveBeenCalled();
  });

  it('exibe mensagem legivel quando a falha nao traz o envelope da plataforma', async () => {
    vi.mocked(createClient).mockRejectedValue(new Error('TypeError: Failed to fetch'));
    const usuario = abrirFormulario();

    await usuario.type(screen.getByLabelText(/Razao social/), 'Industria Alfa');
    await usuario.click(botaoDeEnvio());

    const aviso = await screen.findByRole('alert');
    expect(aviso.textContent).toContain('Nao foi possivel cadastrar o cliente.');
    expect(aviso.textContent).not.toContain('Failed to fetch');
  });

  it('abre o cadastro pelo link da listagem de clientes', async () => {
    const usuario = userEvent.setup();
    renderRoute('/clientes');

    await usuario.click(screen.getByRole('link', { name: 'Cadastrar cliente' }));

    expect(screen.getByRole('heading', { level: 1, name: 'Novo cliente' })).toBeDefined();
  });
});
