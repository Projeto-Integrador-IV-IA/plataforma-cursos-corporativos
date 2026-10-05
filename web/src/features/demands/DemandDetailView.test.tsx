/**
 * Criterios de aceite da tela de detalhe da demanda (RF02).
 *
 * Os testes falam com a tela pelo que o operador ve - bloco, rotulo, botao - e
 * dublam a fronteira de rede (`services/`), nao o `fetch`.
 *
 * `services/demands` e dublado por um servidor de mentira com estado: o PATCH
 * grava e o GET seguinte le o que foi gravado. Sem isso, a revalidacao que
 * vem depois de salvar devolveria o valor antigo e o teste de "edicao
 * refletida" passaria a medir o duble, nao a tela.
 */

import { screen, waitFor, within } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { beforeEach, describe, expect, it, vi } from 'vitest';

import { ApiError } from '@/services/api';
import type { DemandArtifactRead, DemandDetail, DemandUpdate, Uuid } from '@/types/api';

vi.mock('@/services/demands', () => ({
  createDemand: vi.fn(),
  listDemands: vi.fn(),
  getDemand: vi.fn(),
  updateDemand: vi.fn(),
}));

const { getDemand, updateDemand } = await import('@/services/demands');
const { renderRoute } = await import('@/test/renderRoute');

const EMENTA: DemandArtifactRead = {
  id: '33333333-3333-4333-8333-333333333333',
  type: 'EMENTA',
  title: 'Ementa preliminar de NR-12',
  raw_input_id: null,
  created_at: '2026-09-18T11:00:00-03:00',
  versions: [
    {
      id: '44444444-4444-4444-8444-444444444444',
      number: 1,
      content: { tema: 'NR-12' },
      origin: 'IA',
      ai_metadata: { modelo: 'modelo-de-teste' },
      author_id: null,
      created_at: '2026-09-18T11:00:00-03:00',
    },
    {
      id: '55555555-5555-4555-8555-555555555555',
      number: 2,
      content: { tema: 'NR-12 revisado' },
      origin: 'HUMANO',
      ai_metadata: null,
      author_id: '66666666-6666-4666-8666-666666666666',
      created_at: '2026-09-19T09:30:00-03:00',
    },
  ],
};

const DEMANDA: DemandDetail = {
  id: '22222222-2222-4222-8222-222222222222',
  client_id: '11111111-1111-4111-8111-111111111111',
  title: 'Treinamento de NR-12',
  description: 'Vinte e cinco tecnicos da planta 2.',
  owner_id: null,
  status: 'ABERTA',
  current_stage: 'CAPTACAO',
  active: true,
  created_at: '2026-09-17T09:00:00-03:00',
  updated_at: '2026-09-19T09:30:00-03:00',
  client: {
    id: '11111111-1111-4111-8111-111111111111',
    name: 'Industria Alfa',
    cnpj: '12.345.678/0001-90',
    segment: 'Metalurgia',
    contact_name: 'Marina Prado',
    contact_email: 'marina@alfa.example',
    contact_phone: null,
    notes: null,
    active: true,
  },
  artifacts: [EMENTA],
};

/** Estado do servidor de mentira; cada teste comeca do mesmo ponto. */
let persistida: DemandDetail = DEMANDA;

function comDemanda(demanda: DemandDetail) {
  persistida = demanda;
}

beforeEach(() => {
  vi.clearAllMocks();
  persistida = DEMANDA;
  vi.mocked(getDemand).mockImplementation(() => Promise.resolve(persistida));
  vi.mocked(updateDemand).mockImplementation((_demandId: Uuid, payload: DemandUpdate) => {
    persistida = { ...persistida, ...payload };

    return Promise.resolve(persistida);
  });
});

async function abrirDetalhe() {
  const usuario = userEvent.setup();
  renderRoute(`/demandas/${DEMANDA.id}`);
  await screen.findByRole('heading', { level: 2, name: 'Cliente' });

  return usuario;
}

/** Texto visivel na tela inteira, para conferir a presenca de um dado. */
function textoDaTela(): string {
  return document.body.textContent ?? '';
}

describe('detalhe da demanda', () => {
  it('reune contexto, cliente, etapa e artefatos em uma consulta so', async () => {
    await abrirDetalhe();

    expect(getDemand).toHaveBeenCalledTimes(1);
    expect(vi.mocked(getDemand).mock.calls[0]?.[0]).toBe(DEMANDA.id);

    const texto = textoDaTela();
    expect(texto).toContain('Treinamento de NR-12');
    expect(texto).toContain('Vinte e cinco tecnicos da planta 2.');
    expect(texto).toContain('Industria Alfa');
    expect(texto).toContain('12.345.678/0001-90');
    expect(texto).toContain('Metalurgia');
    expect(texto).toContain('Marina Prado');
    expect(texto).toContain('Captacao');
    expect(texto).toContain('Aberta');
    expect(texto).toContain('Ementa preliminar de NR-12');
    // A versao corrente e a ultima da lista, com a origem visivel (RF14).
    expect(texto).toContain('Versao 2 (revisada por pessoa)');
  });

  it('organiza a tela em secoes alcancaveis por um indice', async () => {
    await abrirDetalhe();

    const indice = screen.getByRole('navigation', { name: 'Secoes da demanda' });
    const destinos = within(indice)
      .getAllByRole('link')
      .map((link) => link.getAttribute('href'));

    expect(destinos).toEqual([
      '#demanda-contexto',
      '#demanda-cliente',
      '#demanda-etapa',
      '#demanda-fontes',
      '#demanda-artefatos',
    ]);

    for (const titulo of ['Contexto', 'Cliente', 'Etapa e situacao', 'Fontes captadas', 'Artefatos']) {
      expect(screen.getByRole('heading', { level: 2, name: titulo })).toBeDefined();
    }
  });

  it('leva ao cliente, a captacao, a estruturacao e as versoes do artefato', async () => {
    await abrirDetalhe();

    const destino = (nome: RegExp) =>
      screen.getByRole('link', { name: nome }).getAttribute('href');

    expect(destino(/Industria Alfa/)).toBe(`/clientes/${DEMANDA.client_id}`);
    expect(destino(/Registrar uma fonte/)).toBe(`/demandas/${DEMANDA.id}/ingestao`);
    expect(destino(/Revisar a estruturacao/)).toBe(`/demandas/${DEMANDA.id}/estruturacao`);
    expect(destino(/historico de versoes/)).toBe(`/artefatos/${EMENTA.id}/versoes`);
  });

  it('avisa que as fontes captadas ainda nao estao disponiveis', async () => {
    await abrirDetalhe();

    expect(textoDaTela()).toContain('A listagem das fontes captadas ainda nao esta disponivel');
  });

  it('avisa quando a demanda ainda nao tem artefato', async () => {
    comDemanda({ ...DEMANDA, artifacts: [] });
    await abrirDetalhe();

    expect(textoDaTela()).toContain('Nenhum artefato gerado ate agora');
    expect(screen.queryByRole('link', { name: /historico de versoes/ })).toBeNull();
  });
});

describe('edicao do contexto da demanda', () => {
  it('salva o que foi alterado e reflete na tela', async () => {
    const usuario = await abrirDetalhe();

    await usuario.click(screen.getByRole('button', { name: 'Editar contexto' }));

    const titulo = screen.getByRole('textbox', { name: /Titulo/ });
    await usuario.clear(titulo);
    await usuario.type(titulo, 'Treinamento de NR-12 para a planta 2');
    await usuario.click(screen.getByRole('button', { name: 'Salvar contexto' }));

    await waitFor(() => expect(updateDemand).toHaveBeenCalledTimes(1));
    // So o campo alterado vai no corpo: o PATCH altera somente o que recebe.
    expect(updateDemand).toHaveBeenCalledWith(DEMANDA.id, {
      title: 'Treinamento de NR-12 para a planta 2',
    });

    expect(await screen.findByText('Contexto da demanda salvo.')).toBeDefined();
    await waitFor(() =>
      expect(textoDaTela()).toContain('Treinamento de NR-12 para a planta 2'),
    );
    expect(screen.getByRole('button', { name: 'Editar contexto' })).toBeDefined();
  });

  it('limpa o contexto quando o campo fica vazio', async () => {
    const usuario = await abrirDetalhe();

    await usuario.click(screen.getByRole('button', { name: 'Editar contexto' }));
    await usuario.clear(screen.getByRole('textbox', { name: 'Contexto' }));
    await usuario.click(screen.getByRole('button', { name: 'Salvar contexto' }));

    await waitFor(() => expect(updateDemand).toHaveBeenCalledTimes(1));
    expect(updateDemand).toHaveBeenCalledWith(DEMANDA.id, { description: null });
  });

  it('nao salva enquanto o titulo estiver vazio', async () => {
    const usuario = await abrirDetalhe();

    await usuario.click(screen.getByRole('button', { name: 'Editar contexto' }));
    await usuario.clear(screen.getByRole('textbox', { name: /Titulo/ }));

    const botao = screen.getByRole<HTMLButtonElement>('button', { name: 'Salvar contexto' });
    expect(botao.disabled).toBe(true);
    expect(textoDaTela()).toContain('O titulo identifica a negociacao e nao pode ficar vazio.');

    await usuario.click(botao);
    expect(updateDemand).not.toHaveBeenCalled();
  });

  it('nao envia nada quando o operador nao mudou campo nenhum', async () => {
    const usuario = await abrirDetalhe();

    await usuario.click(screen.getByRole('button', { name: 'Editar contexto' }));

    expect(
      screen.getByRole<HTMLButtonElement>('button', { name: 'Salvar contexto' }).disabled,
    ).toBe(true);
    expect(updateDemand).not.toHaveBeenCalled();
  });

  it('mostra a mensagem da API quando a edicao falha e mantem o formulario aberto', async () => {
    vi.mocked(updateDemand).mockRejectedValue(
      new ApiError({
        kind: 'http',
        code: 'DEMAND_NOT_FOUND',
        message: 'Demanda inexistente.',
        status: 404,
      }),
    );
    const usuario = await abrirDetalhe();

    await usuario.click(screen.getByRole('button', { name: 'Editar contexto' }));
    await usuario.type(screen.getByRole('textbox', { name: 'Contexto' }), ' Turno da noite.');
    await usuario.click(screen.getByRole('button', { name: 'Salvar contexto' }));

    expect(await screen.findByText('Demanda inexistente.')).toBeDefined();
    expect(screen.getByRole('button', { name: 'Salvar contexto' })).toBeDefined();
  });
});

describe('falha ao carregar a demanda', () => {
  it('explica o motivo em vez de mostrar a tela vazia', async () => {
    vi.mocked(getDemand).mockRejectedValue(
      new ApiError({
        kind: 'http',
        code: 'DEMAND_NOT_FOUND',
        message: 'Demanda inexistente.',
        status: 404,
      }),
    );
    renderRoute(`/demandas/${DEMANDA.id}`);

    expect(await screen.findByText('Demanda inexistente.', {}, { timeout: 4000 })).toBeDefined();
    expect(screen.queryByRole('heading', { level: 2, name: 'Cliente' })).toBeNull();
    // O cabecalho da tela continua de pe: o operador sabe onde esta.
    expect(screen.getByRole('heading', { level: 1, name: 'Detalhe da demanda' })).toBeDefined();
  });
});
