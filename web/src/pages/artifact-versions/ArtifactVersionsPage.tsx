/**
 * Historico de versoes de um artefato (RF08).
 *
 * Versoes sao append-only: a restauracao envia o conteudo antigo como uma
 * nova versao humana. Nenhuma versao existente e editada ou removida.
 */

import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';
import { useMemo, useState } from 'react';
import { Link, useParams } from 'react-router-dom';

import { PATHS } from '@/app/paths';
import { ProcessingMessage } from '@/components/ProcessingMessage';
import { formatarDataHora, rotuloDaOrigem } from '@/features/demands/DemandDetailLabels';
import { useFeedback } from '@/hooks/useFeedback';
import { isApiError } from '@/services/api';
import { createArtifactVersion, listArtifactVersions } from '@/services/artifacts';
import type { ArtifactVersion } from '@/types/api';

const PAGE_SIZE = 100;
const FALHA_GENERICA = 'Nao foi possivel carregar as versoes do artefato.';

function mensagemDeErro(error: unknown): string {
  return isApiError(error) ? error.message : FALHA_GENERICA;
}

function autorDaVersao(version: ArtifactVersion): string {
  return version.origin === 'IA' ? 'IA' : version.author_id ?? 'Autor nao informado';
}

export function ArtifactVersionsPage() {
  const { artifactId } = useParams<{ artifactId: string }>();
  const queryClient = useQueryClient();
  const { showSuccess, showError } = useFeedback();
  const [selectedVersion, setSelectedVersion] = useState<number | null>(null);

  const versions = useQuery({
    queryKey: ['artifact-versions', artifactId],
    queryFn: ({ signal }) =>
      listArtifactVersions(artifactId ?? '', { size: PAGE_SIZE }, { signal }),
    enabled: artifactId !== undefined,
  });

  const orderedVersions = useMemo(
    () => [...(versions.data?.items ?? [])].sort((a, b) => b.number - a.number),
    [versions.data],
  );
  const currentVersion = orderedVersions[0]?.number;
  const selected = orderedVersions.find((version) => version.number === selectedVersion);

  const restore = useMutation({
    mutationFn: (version: ArtifactVersion) =>
      createArtifactVersion(artifactId ?? '', { content: version.content }),
    onSuccess: (created) => {
      setSelectedVersion(created.number);
      showSuccess(`Versao ${created.number} criada a partir do historico.`);
      void queryClient.invalidateQueries({ queryKey: ['artifact-versions', artifactId] });
    },
    onError: (error: unknown) => showError(mensagemDeErro(error)),
  });

  if (artifactId === undefined) {
    return (
      <section className="page">
        <h1 className="page__title">Versoes do artefato</h1>
        <p className="page__pending">Artefato nao informado no endereco.</p>
      </section>
    );
  }

  return (
    <section className="page artifact-versions">
      <header className="page__header">
        <h1 className="page__title">Versoes do artefato</h1>
        <p className="page__requirements">
          <span className="tag">RF08</span>
        </p>
        <p className="page__description">
          Historico append-only do artefato {artifactId}. Restaurar uma versao nunca apaga as
          demais: cria uma nova versao vigente.
        </p>
      </header>

      {versions.isPending ? (
        <p className="page__pending" role="status">
          Carregando versoes…
        </p>
      ) : null}

      {versions.isError ? (
        <div className="demand-detail__failure" role="alert">
          <p>{mensagemDeErro(versions.error)}</p>
          <button type="button" className="button" onClick={() => void versions.refetch()}>
            Tentar novamente
          </button>
        </div>
      ) : null}

      {versions.isSuccess && orderedVersions.length === 0 ? (
        <p className="demand-detail__empty" role="status">
          Nenhuma versao registrada para este artefato.
        </p>
      ) : null}

      {versions.isSuccess && orderedVersions.length > 0 ? (
        <>
          <p className="artifact-versions__current">
            Versao vigente: <strong>Versao {currentVersion}</strong>. A lista permanece completa
            depois de qualquer restauracao.
          </p>
          <ol className="artifact-versions__list">
            {orderedVersions.map((version) => {
              const isCurrent = version.number === currentVersion;
              const isRestoring = restore.isPending && restore.variables?.number === version.number;

              return (
                <li
                  className={`artifact-versions__item${isCurrent ? ' artifact-versions__item--current' : ''}`}
                  key={version.id}
                >
                  <div className="artifact-versions__heading">
                    <h2>Versao {version.number}</h2>
                    {isCurrent ? <span className="tag">Vigente</span> : null}
                  </div>
                  <p className="artifact-versions__meta">
                    Autor: {autorDaVersao(version)} · Origem: {rotuloDaOrigem(version.origin)} ·
                    Criada em {formatarDataHora(version.created_at)}
                  </p>
                  <div className="form__actions">
                    <button
                      type="button"
                      className="button button--secondary"
                      onClick={() => setSelectedVersion(version.number)}
                    >
                      Ver conteudo
                    </button>
                    {!isCurrent ? (
                      <button
                        type="button"
                        className="button"
                        disabled={restore.isPending}
                        onClick={() => restore.mutate(version)}
                      >
                        {isRestoring ? 'Restaurando…' : 'Restaurar como nova versao'}
                      </button>
                    ) : null}
                  </div>
                </li>
              );
            })}
          </ol>

          {restore.isPending ? <ProcessingMessage operation="restauracao da versao" /> : null}

          {selected !== undefined ? (
            <section className="artifact-versions__content" aria-labelledby="versao-selecionada">
              <h2 id="versao-selecionada">Conteudo da versao {selected.number}</h2>
              <pre>{JSON.stringify(selected.content, null, 2)}</pre>
            </section>
          ) : (
            <p className="artifact-versions__hint" role="status">
              Escolha uma versao para visualizar o conteudo preservado.
            </p>
          )}
        </>
      ) : null}

      <p className="page__description">
        <Link to={PATHS.demands}>Voltar para a lista de demandas</Link>
      </p>
    </section>
  );
}
