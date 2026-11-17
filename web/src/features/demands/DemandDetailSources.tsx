import { Link } from "react-router-dom";

import { buildPath } from "@/app/paths";
import { formatarDataHora } from "@/features/demands/DemandDetailLabels";
import { rotuloDaFonte } from "@/features/demands/DemandStructuringLabels";
import type { DemandRawInputRead, Uuid } from "@/types/api";

interface DemandDetailSourcesProps {
  demandId: Uuid;
  sources: readonly DemandRawInputRead[];
}

const TAMANHO_PREVIA = 280;

export function DemandDetailSources({
  demandId,
  sources,
}: DemandDetailSourcesProps) {
  if (sources.length === 0) {
    return (
      <>
        <p className="demand-detail__empty">
          Ainda falta registrar o texto recebido do cliente para gerar o curso
          com IA.
        </p>
        <div className="demand-detail__actions">
          <Link
            className="button button--secondary"
            to={buildPath.demandIngestion(demandId)}
          >
            Registrar a primeira fonte da demanda
          </Link>
        </div>
      </>
    );
  }

  return (
    <ul className="demand-detail__artifacts">
      {sources.map((source) => (
        <li className="demand-detail__artifact" key={source.id}>
          <h3 className="demand-detail__artifact-title">
            {rotuloDaFonte(source.source)} ·{" "}
            {formatarDataHora(source.created_at)}
          </h3>
          <p className="demand-detail__artifact-meta">
            {source.original_content.length > TAMANHO_PREVIA
              ? `${source.original_content.slice(0, TAMANHO_PREVIA).trimEnd()}…`
              : source.original_content}
          </p>
          {source.truncated ? (
            <p className="demand-detail__artifact-meta">
              O texto original foi marcado como truncado na captação.
            </p>
          ) : null}
        </li>
      ))}
      <li>
        <Link
          className="button button--secondary"
          to={buildPath.demandIngestion(demandId)}
        >
          Adicionar outra fonte
        </Link>
      </li>
    </ul>
  );
}
