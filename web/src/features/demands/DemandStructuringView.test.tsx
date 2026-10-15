/**
 * Criterios de aceite da revisao da estruturacao (RF19).
 *
 * Os testes falam com a tela pelo que o operador ve - secao, rotulo, valor - e
 * dublam a fronteira de rede (`services/`), nao o `fetch`.
 *
 * A estrutura dublada e a do contrato: `structured_content` chega como objeto
 * JSON aberto, do jeito que `GET /api/v1/demands/{id}/artifacts` o devolve, e
 * as fontes chegam separadas - vinculo no artefato, texto no agregado da
 * demanda. Dublar as duas pontas e o que prova que a tela liga uma na outra.
 */

import { screen, within } from '@testing-library/react';
import { beforeEach, describe, expect, it, vi } from 'vitest';

import { ApiError } from '@/services/api';
import type {
  ArtifactResultRead,
  DemandDetail,
  DemandRawInputRead,
  JsonObject,
} from '@/types/api';

vi.mock('@/services/demands', () => ({
  createDemand: vi.fn(),
  listDemands: vi.fn(),
  getDemand: vi.fn(),
  updateDemand: vi.fn(),
}));

vi.mock('@/services/artifacts', () => ({
  listArtifacts: vi.fn(),
  getArtifact: vi.fn(),
  listArtifactVersions: vi.fn(),
  getArtifactVersion: vi.fn(),
  createArtifactVersion: vi.fn(),
}));

const { getDemand } = await import('@/services/demands');
const { listArtifacts } = await import('@/services/artifacts');
const { renderRoute } = await import('@/test/renderRoute');

const DEMAND_ID = '22222222-2222-4222-8222-222222222222';
const FONTE_ID = '77777777-7777-4777-8777-777777777777';

const CURSO: JsonObject = {
  tema: 'NR-12 (seguranca em maquinas e equipamentos)',
  nicho: 'Metalurgia',
  publico_alvo: 'Tecnicos de manutencao da planta 2',
  numero_participantes: 25,
  carga_horaria: 16,
  formato: 'presencial',
  objetivos_aprendizagem: ['Identificar zonas de risco em prensas'],
  ementa: [
    {
      titulo: 'Fundamentos da NR-12',
      topicos: ['Campo de aplicacao', 'Responsabilidades'],
      carga_horaria: 8,
    },
  ],
  campos_ausentes: [],
  observacoes: ['O cliente nao confirmou a data de realizacao.'],
};

const FONTE: DemandRawInputRead = {
  id: FONTE_ID,
  source: 'EMAIL',
  original_content: 'Precisamos de um treinamento de NR-12 para uns 25 tecnicos.',
  truncated: false,
  author_id: '66666666-6666-4666-8666-666666666666',
  created_at: '2026-10-10T09:00:00-03:00',
};

const DEMANDA: DemandDetail = {
  id: DEMAND_ID,
  client_id: '11111111-1111-4111-8111-111111111111',
  title: 'Treinamento de NR-12',
  description: 'Vinte e cinco tecnicos da planta 2.',
  owner_id: null,
  status: 'ABERTA',
  current_stage: 'ESTRUTURACAO',
  active: true,
  created_at: '2026-10-10T09:00:00-03:00',
  updated_at: '2026-10-12T09:30:00-03:00',
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
  raw_inputs: [FONTE],
  artifacts: [],
};

function artefatoCom(content: JsonObject): ArtifactResultRead {
  return {
    id: '33333333-3333-4333-8333-333333333333',
    demand_id: DEMAND_ID,
    type: 'REQUISITOS_EXTRAIDOS',
    title: 'Requisitos extraidos de NR-12',
    created_at: '2026-10-12T09:30:00-03:00',
    sources: [{ id: FONTE_ID, source: 'EMAIL', created_at: FONTE.created_at }],
    versions: [
      {
        id: '44444444-4444-4444-8444-444444444444',
        number: 1,
        raw_output: '{"tema": "NR-12"}',
        structured_content: content,
        origin: 'IA',
        ai_metadata: { modelo: 'modelo-de-teste' },
        created_at: '2026-10-12T09:30:00-03:00',
      },
    ],
  };
}

beforeEach(() => {
  vi.clearAllMocks();
  vi.mocked(getDemand).mockResolvedValue(DEMANDA);
  vi.mocked(listArtifacts).mockResolvedValue([artefatoCom(CURSO)]);
});

async function abrirRevisao() {
  renderRoute(`/demandas/${DEMAND_ID}/estruturacao`);
  await screen.findByRole('heading', { level: 2, name: 'Estrutura gerada' });
}

/** Texto visivel na tela inteira, para conferir a presenca de um dado. */
function textoDaTela(): string {
  return document.body.textContent ?? '';
}

describe('revisao da estruturacao', () => {
  it('apresenta a estrutura gerada por inteiro', async () => {
    await abrirRevisao();

    expect(getDemand).toHaveBeenCalledTimes(1);
    expect(listArtifacts).toHaveBeenCalledTimes(1);
    expect(vi.mocked(listArtifacts).mock.calls[0]?.[0]).toBe(DEMAND_ID);

    const texto = textoDaTela();
    // Os campos extraidos (RF11), com unidade onde ela muda a leitura.
    expect(texto).toContain('NR-12 (seguranca em maquinas e equipamentos)');
    expect(texto).toContain('Metalurgia');
    expect(texto).toContain('Tecnicos de manutencao da planta 2');
    expect(texto).toContain('25 participantes');
    expect(texto).toContain('16 horas');
    expect(texto).toContain('Presencial');
    // Os campos gerados (RF12) e a observacao do modelo.
    expect(texto).toContain('Identificar zonas de risco em prensas');
    expect(texto).toContain('Fundamentos da NR-12');
    expect(texto).toContain('Campo de aplicacao');
    expect(texto).toContain('O cliente nao confirmou a data de realizacao.');
  });

  it('mostra a versao e a origem do que esta sendo revisado', async () => {
    await abrirRevisao();

    const texto = textoDaTela();
    expect(texto).toContain('Versao 1');
    expect(texto).toContain('gerada pela IA');
  });

  it('declara a ausencia em vez de deixar o campo em branco', async () => {
    vi.mocked(listArtifacts).mockResolvedValue([
      artefatoCom({
        ...CURSO,
        publico_alvo: null,
        carga_horaria: 0,
        objetivos_aprendizagem: [],
        ementa: [],
      }),
    ]);

    await abrirRevisao();

    const texto = textoDaTela();
    expect(texto).toContain('Nao informado');
    expect(texto).toContain('A estrutura nao traz objetivos de aprendizagem.');
    expect(texto).toContain('A estrutura nao traz modulos de ementa.');
  });

  it('da acesso as fontes que originaram a estrutura', async () => {
    await abrirRevisao();

    const secao = screen.getByRole('region', { name: 'Fontes de origem' });
    expect(within(secao).getByText('E-mail')).toBeDefined();
    expect(within(secao).getByText(/Precisamos de um treinamento de NR-12/)).toBeDefined();
    expect(
      within(secao).getByRole('link', { name: 'Ver a captacao desta demanda' }),
    ).toBeDefined();
  });

  it('anuncia que nada foi anexado quando a demanda nao tem estrutura', async () => {
    vi.mocked(listArtifacts).mockResolvedValue([]);

    await abrirRevisao();

    expect(textoDaTela()).toContain('Nenhuma estrutura foi anexada a esta demanda');
  });

  it('destaca os tres tipos de lacuna e os distingue entre si', async () => {
    vi.mocked(listArtifacts).mockResolvedValue([
      artefatoCom({
        ...CURSO,
        campos_ausentes: [
          { campo: 'nicho', tipo: 'ausente', motivo: 'O cliente nao disse o setor.' },
          { campo: 'carga_horaria', tipo: 'ambigua', motivo: '"Dois dias" pode ser 8 ou 16 horas.' },
          {
            campo: 'numero_participantes',
            tipo: 'contraditoria',
            motivo: 'O texto fala de 25 e depois de 40 tecnicos.',
          },
        ],
      }),
    ]);

    await abrirRevisao();

    const texto = textoDaTela();
    // Cada tipo e nomeado por escrito: a distincao nao depende de cor.
    expect(texto).toContain('Ausente');
    expect(texto).toContain('Ambigua');
    expect(texto).toContain('Contraditoria');
    // E cada tipo pede uma conversa diferente com o cliente.
    expect(texto).toContain('a fonte nao traz esta informacao: pergunte ao cliente.');
    expect(texto).toContain('a fonte admite mais de uma leitura: esclareca com o cliente.');
    expect(texto).toContain('a fonte se contradiz neste ponto: confronte os trechos com o cliente.');
    // E o motivo de cada lacuna fica acessivel na tela.
    expect(texto).toContain('O cliente nao disse o setor.');
    expect(texto).toContain('"Dois dias" pode ser 8 ou 16 horas.');
    expect(texto).toContain('O texto fala de 25 e depois de 40 tecnicos.');

    const lacunas = screen.getByRole('region', { name: /Campos a confirmar/ });
    expect(within(lacunas).getAllByRole('listitem')).toHaveLength(3);
  });

  it('marca o campo lido com a forma propria do tipo da lacuna', async () => {
    vi.mocked(listArtifacts).mockResolvedValue([
      artefatoCom({
        ...CURSO,
        campos_ausentes: [
          { campo: 'nicho', tipo: 'ausente', motivo: null },
          { campo: 'carga_horaria', tipo: 'ambigua', motivo: null },
          { campo: 'ementa', tipo: 'contraditoria', motivo: null },
        ],
      }),
    ]);

    await abrirRevisao();

    // Forma, e nao cor: cada tipo marca o campo com uma classe propria, que o
    // CSS traduz em borda tracejada, pontilhada ou dupla.
    expect(document.querySelectorAll('.structuring-gap-host--ausente').length).toBeGreaterThan(0);
    expect(document.querySelectorAll('.structuring-gap-host--ambigua').length).toBeGreaterThan(0);
    expect(
      document.querySelectorAll('.structuring-gap-host--contraditoria').length,
    ).toBeGreaterThan(0);
    // Lacuna sem motivo continua visivel, declarando que o motivo nao veio.
    expect(textoDaTela()).toContain('O modelo nao registrou o motivo desta lacuna.');
  });

  it('nao perde lacuna de campo que a tela nao apresenta', async () => {
    vi.mocked(listArtifacts).mockResolvedValue([
      artefatoCom({
        ...CURSO,
        campos_ausentes: [
          { campo: 'orcamento', tipo: 'ausente', motivo: 'Campo fora dos apresentados.' },
        ],
      }),
    ]);

    await abrirRevisao();

    const lacunas = screen.getByRole('region', { name: /Campos a confirmar/ });
    expect(within(lacunas).getByText('orcamento')).toBeDefined();
    expect(within(lacunas).getByText(/Campo fora dos apresentados\./)).toBeDefined();
  });

  it('diz quando a estruturacao nao apontou lacuna nenhuma', async () => {
    await abrirRevisao();

    expect(textoDaTela()).toContain('A estruturacao nao apontou lacuna nenhuma.');
  });

  it('mostra a mensagem do servico quando a consulta falha', async () => {
    vi.mocked(listArtifacts).mockRejectedValue(
      new ApiError({
        kind: 'http',
        code: 'DEMAND_NOT_FOUND',
        message: 'Demanda nao encontrada.',
        status: 404,
      }),
    );

    renderRoute(`/demandas/${DEMAND_ID}/estruturacao`);

    // `timeout` folgado: o cliente de dados ainda tenta a consulta uma vez.
    expect(
      await screen.findByText('Demanda nao encontrada.', undefined, { timeout: 4000 }),
    ).toBeDefined();
  });
});
