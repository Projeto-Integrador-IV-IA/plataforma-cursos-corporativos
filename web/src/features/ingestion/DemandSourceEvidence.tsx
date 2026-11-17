import { useEffect } from 'react';
import { Link } from 'react-router-dom';

import { formatarDataHora } from '@/features/demands/DemandDetailLabels';
import { rotuloDaFonte } from '@/features/demands/DemandStructuringLabels';
import type { DemandRawInputRead, SourceSegmentRead } from '@/types/api';

interface DemandSourceEvidenceProps {
  readonly source: DemandRawInputRead;
  readonly segment: SourceSegmentRead;
  readonly segments: readonly SourceSegmentRead[];
  readonly returnTo: { pathname: string; search: string; hash: string };
}

interface TextRange {
  readonly start: number;
  readonly end: number;
}

function utf16Offset(sourceText: string, characterOffset: number): number | null {
  if (characterOffset < 0) return null;

  let characters = 0;
  let codeUnits = 0;
  for (const character of sourceText) {
    if (characters === characterOffset) return codeUnits;
    characters += 1;
    codeUnits += character.length;
  }

  return characters === characterOffset ? codeUnits : null;
}

function highlightRange(sourceText: string, segment: SourceSegmentRead): TextRange | null {
  const { original_start_offset: start, original_end_offset: end, original_content: quote } = segment;
  const startIndex = start === null ? null : utf16Offset(sourceText, start);
  const endIndex = end === null ? null : utf16Offset(sourceText, end);

  if (
    startIndex !== null &&
    endIndex !== null &&
    endIndex > startIndex
  ) {
    if (quote === null || sourceText.slice(startIndex, endIndex) === quote) {
      return { start: startIndex, end: endIndex };
    }
  }

  if (quote === null || quote.length === 0) return null;

  const firstMatch = sourceText.indexOf(quote);
  return firstMatch >= 0 && sourceText.indexOf(quote, firstMatch + 1) === -1
    ? { start: firstMatch, end: firstMatch + quote.length }
    : null;
}

export function DemandSourceEvidence({
  source,
  segment,
  segments,
  returnTo,
}: DemandSourceEvidenceProps) {
  const sourceSegments = segments
    .filter((item) => item.raw_input_id === source.id)
    .slice()
    .sort((left, right) => left.position - right.position);
  const selectedIndex = sourceSegments.findIndex((item) => item.id === segment.id);
  const previous = selectedIndex > 0 ? sourceSegments[selectedIndex - 1] : undefined;
  const next = selectedIndex < 0 ? undefined : sourceSegments[selectedIndex + 1];
  const range = highlightRange(source.original_content, segment);

  useEffect(() => {
    document.getElementById('source-evidence')?.scrollIntoView?.({ block: 'start' });
  }, [segment.id, source.id]);

  return (
    <section
      className="source-evidence"
      id="source-evidence"
      aria-labelledby="source-evidence-title"
    >
      <header className="source-evidence__header">
        <div>
          <h3 className="source-evidence__title" id="source-evidence-title">
            Fonte original
          </h3>
          <p className="source-evidence__meta">
            {rotuloDaFonte(source.source)} · captada em {formatarDataHora(source.created_at)}
          </p>
        </div>
        <Link className="source-evidence__back" to={returnTo}>
          Voltar para a revisao
        </Link>
      </header>

      {source.truncated ? (
        <p className="source-evidence__notice">
          A fonte foi cortada no limite de tamanho da captacao; o conteudo abaixo e o que foi
          preservado.
        </p>
      ) : null}

      <section aria-labelledby="source-evidence-context">
        <h4 className="source-evidence__section-title" id="source-evidence-context">
          Trecho citado e contexto
        </h4>
        <ol className="source-evidence__neighbors">
          {previous === undefined ? null : (
            <li className="source-evidence__neighbor">
              <span className="source-evidence__neighbor-label">Trecho anterior</span>
              <p>{previous.content}</p>
            </li>
          )}
          <li className="source-evidence__neighbor source-evidence__neighbor--selected">
            <span className="source-evidence__neighbor-label">
              Evidencia selecionada · posicao {segment.position} na fonte
            </span>
            <p>{segment.content}</p>
          </li>
          {next === undefined ? null : (
            <li className="source-evidence__neighbor">
              <span className="source-evidence__neighbor-label">Trecho seguinte</span>
              <p>{next.content}</p>
            </li>
          )}
        </ol>
      </section>

      <section aria-labelledby="source-evidence-full">
        <h4 className="source-evidence__section-title" id="source-evidence-full">
          Texto completo da fonte
        </h4>
        <p className="source-evidence__text">
          {range === null ? (
            source.original_content
          ) : (
            <>
              {source.original_content.slice(0, range.start)}
              <mark className="source-evidence__highlight">
                {source.original_content.slice(range.start, range.end)}
              </mark>
              {source.original_content.slice(range.end)}
            </>
          )}
        </p>
        {range === null ? (
          <p className="source-evidence__notice" role="status">
            Nao foi possivel destacar automaticamente este trecho legado; a citacao e exibida acima
            para conferencia manual.
          </p>
        ) : null}
      </section>
    </section>
  );
}
