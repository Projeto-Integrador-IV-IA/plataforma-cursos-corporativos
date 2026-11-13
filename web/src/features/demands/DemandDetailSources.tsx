import { Link } from 'react-router-dom';

import { buildPath } from '@/app/paths';
import { DemandSourceEvidence } from '@/features/ingestion/DemandSourceEvidence';
import { formatarDataHora } from '@/features/demands/DemandDetailLabels';
import { rotuloDaFonte } from '@/features/demands/DemandStructuringLabels';
import type { DemandRawInputRead, SourceSegmentRead, Uuid } from '@/types/api';

interface DemandDetailSourcesProps {
  readonly demandId: Uuid;
  readonly rawInputs: readonly DemandRawInputRead[];
  readonly segments: readonly SourceSegmentRead[];
  readonly selectedSourceId: string | null;
  readonly selectedSegmentId: string | null;
  readonly returnTo: { pathname: string; search: string; hash: string };
}

export function DemandDetailSources({
  demandId,
  rawInputs,
  segments,
  selectedSourceId,
  selectedSegmentId,
  returnTo,
}: DemandDetailSourcesProps) {
  const evidenceRequested = selectedSourceId !== null || selectedSegmentId !== null;

  if (rawInputs.length === 0) {
    return (
      <>
        <p className="demand-detail__empty">
          {evidenceRequested
            ? 'A fonte ou o trecho citado nao foi encontrado nesta demanda.'
            : 'Nenhuma fonte captada foi registrada nesta demanda.'}
        </p>
        {evidenceRequested ? (
          <p className="page__description">
            <Link to={returnTo}>Voltar para a revisao</Link>
          </p>
        ) : null}
        <p className="page__description">
          <Link to={buildPath.demandIngestion(demandId)}>Registrar uma fonte na captacao</Link>
        </p>
      </>
    );
  }

  const selectedSource =
    selectedSourceId === null
      ? undefined
      : rawInputs.find((source) => source.id === selectedSourceId);
  const selectedSegment =
    selectedSource === undefined || selectedSegmentId === null
      ? undefined
      : segments.find(
          (segment) =>
            segment.id === selectedSegmentId && segment.raw_input_id === selectedSource.id,
        );

  return (
    <>
      {evidenceRequested ? (
        selectedSourceId === null ||
        selectedSegmentId === null ||
        selectedSource === undefined ||
        selectedSegment === undefined ? (
          <>
            <p className="demand-detail__failure" role="alert">
              A fonte ou o trecho citado nao foi encontrado nesta demanda.
            </p>
            <p className="page__description">
              <Link to={returnTo}>Voltar para a revisao</Link>
            </p>
          </>
        ) : (
          <DemandSourceEvidence
            source={selectedSource}
            segment={selectedSegment}
            segments={segments}
            returnTo={returnTo}
          />
        )
      ) : (
        <ul className="demand-detail__sources">
          {rawInputs.map((source) => (
            <li className="demand-detail__source" key={source.id}>
              <p className="demand-detail__source-title">
                <span className="tag">{rotuloDaFonte(source.source)}</span> Captada em{' '}
                {formatarDataHora(source.created_at)}
              </p>
              {source.truncated ? (
                <p className="demand-detail__source-notice">
                  Texto cortado no limite de tamanho da captacao.
                </p>
              ) : null}
              <details>
                <summary>Ver o texto completo</summary>
                <p className="demand-detail__source-content">{source.original_content}</p>
              </details>
            </li>
          ))}
        </ul>
      )}
      <p className="page__description">
        <Link to={buildPath.demandIngestion(demandId)}>Registrar uma fonte na captacao</Link>
      </p>
    </>
  );
}
