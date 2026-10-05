/**
 * Cobre o modulo de demandas, unica operacao ja declarada no contrato
 * (`POST /api/v1/demands` em `pipeline-service.yaml`).
 *
 * Alem do comportamento, o teste fixa a tipagem: `expectTypeOf` falha na
 * compilacao (`npm run build`) se o tipo devolvido deixar de ser `DemandRead` -
 * que e o criterio de aceite de RNF02.
 */

import { afterEach, describe, expect, expectTypeOf, it, vi } from 'vitest';

import { ApiError, isApiError } from '@/services/api';
import { createDemand, getDemand, listDemands, updateDemand } from '@/services/demands';
import type { DemandRead, Page } from '@/types/api';

const BASE_URL = 'https://gateway.test/api/v1';

const DEMANDA: DemandRead = {
  id: '11111111-1111-1111-1111-111111111111',
  client_id: '22222222-2222-2222-2222-222222222222',
  title: 'Formacao de lideranca',
  description: null,
  owner_id: null,
  status: 'ABERTA',
  current_stage: 'CAPTACAO',
  active: true,
  created_at: '2026-09-15T14:30:00-03:00',
  updated_at: '2026-09-15T14:30:00-03:00',
};

const calls: { url: string; init: RequestInit | undefined }[] = [];

function stubFetch(body: unknown, status = 200): void {
  vi.stubGlobal(
    'fetch',
    vi.fn((input: RequestInfo | URL, init?: RequestInit) => {
      calls.push({ url: String(input), init });

      return Promise.resolve(
        new Response(JSON.stringify(body), {
          status,
          headers: { 'Content-Type': 'application/json' },
        }),
      );
    }),
  );
}

function lastCall(): { url: string; init: RequestInit | undefined } {
  const call = calls.at(-1);

  if (call === undefined) {
    throw new Error('Nenhuma requisicao foi capturada.');
  }

  return call;
}

afterEach(() => {
  calls.length = 0;
  vi.unstubAllGlobals();
  vi.unstubAllEnvs();
});

describe('createDemand', () => {
  it('envia o corpo do contrato e devolve a demanda criada', async () => {
    vi.stubEnv('VITE_API_BASE_URL', BASE_URL);
    stubFetch(DEMANDA, 201);

    const criada = await createDemand({
      client_id: DEMANDA.client_id,
      title: DEMANDA.title,
    });

    expectTypeOf(criada).toEqualTypeOf<DemandRead>();
    expect(criada).toEqual(DEMANDA);
    expect(lastCall().url).toBe(`${BASE_URL}/demands`);
    expect(lastCall().init?.method).toBe('POST');
    expect(lastCall().init?.body).toBe(
      JSON.stringify({ client_id: DEMANDA.client_id, title: DEMANDA.title }),
    );
  });

  it('propaga o erro do contrato quando o cliente nao existe', async () => {
    vi.stubEnv('VITE_API_BASE_URL', BASE_URL);
    stubFetch(
      { error: { code: 'CLIENT_NOT_FOUND', message: 'Cliente inexistente.' } },
      404,
    );

    const erro: unknown = await createDemand({ client_id: 'inexistente', title: 'X' }).catch(
      (motivo: unknown) => motivo,
    );

    expect(erro).toBeInstanceOf(ApiError);
    expect(isApiError(erro) && erro.code).toBe('CLIENT_NOT_FOUND');
  });
});

describe('listDemands', () => {
  it('traduz os filtros de RF03 em query string, omitindo o que nao foi informado', async () => {
    vi.stubEnv('VITE_API_BASE_URL', BASE_URL);
    stubFetch({ items: [DEMANDA], total: 1, page: 1, size: 20 });

    const pagina = await listDemands({
      status: 'ABERTA',
      client_id: DEMANDA.client_id,
      limit: 20,
      offset: 20,
    });

    expectTypeOf(pagina).toEqualTypeOf<Page<DemandRead>>();
    expect(pagina.items).toHaveLength(1);
    // Entrada em limit/offset, como o contrato declara; a resposta e que volta paginada.
    expect(lastCall().url).toBe(
      `${BASE_URL}/demands?limit=20&offset=20&status=ABERTA&client_id=${DEMANDA.client_id}`,
    );
  });
});

describe('getDemand e updateDemand', () => {
  it('usam o caminho do recurso com o identificador', async () => {
    vi.stubEnv('VITE_API_BASE_URL', BASE_URL);
    stubFetch(DEMANDA);

    await getDemand(DEMANDA.id);
    expect(lastCall().url).toBe(`${BASE_URL}/demands/${DEMANDA.id}`);

    await updateDemand(DEMANDA.id, { title: 'Formacao de lideranca II' });
    expect(lastCall().init?.method).toBe('PATCH');
    expect(lastCall().init?.body).toBe(JSON.stringify({ title: 'Formacao de lideranca II' }));
  });
});
