/**
 * Verifica que cada modulo de dominio fala com o gateway pelo cliente unico e
 * no caminho acordado em docs/02-arquitetura/contratos-api.md.
 *
 * Enquanto os contratos desses dominios forem esqueleto, este teste e o que
 * documenta a forma da chamada: quando o contrato for publicado, e aqui que a
 * divergencia de caminho aparece primeiro.
 */

import { afterEach, describe, expect, it, vi } from 'vitest';

import { listArtifactVersions } from '@/services/artifacts';
import { createClient, listClients } from '@/services/clients';
import { createRawInput } from '@/services/ingestion';
import { listStageTransitions, revertDemandStage } from '@/services/pipeline';

const BASE_URL = 'https://gateway.test/api/v1';
const DEMAND_ID = '11111111-1111-1111-1111-111111111111';
const ARTIFACT_ID = '33333333-3333-3333-3333-333333333333';

const calls: { url: string; init: RequestInit | undefined }[] = [];

function stubFetch(body: unknown = {}): void {
  vi.stubGlobal(
    'fetch',
    vi.fn((input: RequestInfo | URL, init?: RequestInit) => {
      calls.push({ url: String(input), init });

      return Promise.resolve(
        new Response(JSON.stringify(body), {
          status: 200,
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

describe('modulos de dominio', () => {
  it('clientes: lista com filtro e cadastra (RF01, RF03)', async () => {
    vi.stubEnv('VITE_API_BASE_URL', BASE_URL);
    stubFetch({ items: [], total: 0, page: 1, size: 20 });

    await listClients({ search: 'acme', active: true });
    expect(lastCall().url).toBe(`${BASE_URL}/clients?search=acme&active=true`);

    await createClient({ name: 'Acme' });
    expect(lastCall().url).toBe(`${BASE_URL}/clients`);
    expect(lastCall().init?.method).toBe('POST');
  });

  it('ingestao: registra a demanda bruta na demanda (RF09, RNF05)', async () => {
    vi.stubEnv('VITE_API_BASE_URL', BASE_URL);
    stubFetch();

    await createRawInput(DEMAND_ID, { original_content: 'texto como chegou', source: 'EMAIL' });

    expect(lastCall().url).toBe(`${BASE_URL}/ingestion/demands/${DEMAND_ID}/raw-inputs`);
    expect(lastCall().init?.body).toBe(
      JSON.stringify({ original_content: 'texto como chegou', source: 'EMAIL' }),
    );
  });

  it('pipeline: retrocesso leva justificativa e historico e subrecurso (RF06, RF07)', async () => {
    vi.stubEnv('VITE_API_BASE_URL', BASE_URL);
    stubFetch();

    await revertDemandStage(DEMAND_ID, 'CAPTACAO', 'Cliente pediu revisao do escopo');
    expect(lastCall().url).toBe(`${BASE_URL}/demands/${DEMAND_ID}/transitions`);
    expect(lastCall().init?.body).toBe(
      JSON.stringify({ to_stage: 'CAPTACAO', reason: 'Cliente pediu revisao do escopo' }),
    );

    await listStageTransitions(DEMAND_ID);
    expect(lastCall().url).toBe(`${BASE_URL}/demands/${DEMAND_ID}/transitions`);
    expect(lastCall().init?.method).toBe('GET');
  });

  it('artefatos: versoes ficam sob o artefato (RF08)', async () => {
    vi.stubEnv('VITE_API_BASE_URL', BASE_URL);
    stubFetch({ items: [], total: 0, page: 1, size: 20 });

    await listArtifactVersions(ARTIFACT_ID, { page: 1, size: 50 });

    expect(lastCall().url).toBe(`${BASE_URL}/artifacts/${ARTIFACT_ID}/versions?page=1&size=50`);
  });
});
