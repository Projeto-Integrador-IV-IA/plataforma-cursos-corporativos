import { screen, waitFor } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { beforeEach, describe, expect, it, vi } from 'vitest';

import type { ArtifactVersion, JsonObject, Page } from '@/types/api';

vi.mock('@/services/artifacts', () => ({
  listArtifactVersions: vi.fn(),
  createArtifactVersion: vi.fn(),
}));

const { createArtifactVersion, listArtifactVersions } = await import('@/services/artifacts');
const { renderRoute } = await import('@/test/renderRoute');

const ARTIFACT_ID = '33333333-3333-4333-8333-333333333333';
const AUTHOR_ID = '44444444-4444-4444-8444-444444444444';

function version(number: number, content: JsonObject, origin: 'IA' | 'HUMANO'): ArtifactVersion {
  return {
    id: `version-${number}`,
    artifact_id: ARTIFACT_ID,
    number,
    content,
    origin,
    ai_metadata: origin === 'IA' ? { modelo: 'modelo-teste' } : null,
    author_id: origin === 'IA' ? null : AUTHOR_ID,
    created_at: `2026-10-${String(10 + number).padStart(2, '0')}T09:00:00-03:00`,
  };
}

const VERSIONS: Page<ArtifactVersion> = {
  items: [version(2, { tema: 'Escopo atual' }, 'HUMANO'), version(1, { tema: 'Escopo antigo' }, 'IA')],
  total: 2,
  page: 1,
  size: 100,
};

beforeEach(() => {
  vi.clearAllMocks();
  vi.mocked(listArtifactVersions).mockResolvedValue(VERSIONS);
  vi.mocked(createArtifactVersion).mockResolvedValue(
    version(3, { tema: 'Escopo antigo' }, 'HUMANO'),
  );
});

describe('historico de versoes do artefato', () => {
  it('lista autor e data e permite visualizar uma versao anterior', async () => {
    const user = userEvent.setup();
    renderRoute(`/artefatos/${ARTIFACT_ID}/versoes`);

    expect(await screen.findByRole('heading', { name: 'Versao 2' })).toBeDefined();
    expect(screen.getByText(`Autor: ${AUTHOR_ID}`)).toBeDefined();
    expect(screen.getByText(/Criada em/)).toBeDefined();

    await user.click(screen.getAllByRole('button', { name: 'Ver conteudo' })[1]!);

    expect(screen.getByRole('heading', { name: 'Conteudo da versao 1' })).toBeDefined();
    expect(screen.getByText(/Escopo antigo/)).toBeDefined();
  });

  it('restaura uma versao enviando seu conteudo como nova versao', async () => {
    const user = userEvent.setup();
    renderRoute(`/artefatos/${ARTIFACT_ID}/versoes`);
    await screen.findByRole('heading', { name: 'Versao 2' });

    await user.click(screen.getByRole('button', { name: 'Restaurar como nova versao' }));

    await waitFor(() =>
      expect(createArtifactVersion).toHaveBeenCalledWith(ARTIFACT_ID, {
        content: { tema: 'Escopo antigo' },
      }),
    );
    expect(screen.getByText(/Restaurar uma versao nunca apaga as demais/)).toBeDefined();
  });
});
