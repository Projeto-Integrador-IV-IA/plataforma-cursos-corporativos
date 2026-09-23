/**
 * Artefatos da demanda vistos a partir do detalhe (RF08, RF15).
 *
 * O agregado ja chega com as versoes de cada artefato em ordem crescente, e o
 * detalhe mostra a ultima delas - a corrente. O historico completo fica na
 * tela de versoes, a um link daqui: repetir todas as versoes aqui afogaria a
 * leitura da negociacao, que e o que esta tela existe para dar.
 *
 * A origem de cada versao aparece junto com o numero porque RF14 depende disso:
 * quem le precisa distinguir o que a IA gerou do que uma pessoa revisou antes
 * de levar qualquer coisa ao cliente.
 */

import { Link } from 'react-router-dom';

import { buildPath } from '@/app/paths';
import {
  formatarDataHora,
  rotuloDaOrigem,
  rotuloDoTipoDeArtefato,
} from '@/features/demands/DemandDetailLabels';
import type { DemandArtifactRead } from '@/types/api';

interface DemandDetailArtifactsProps {
  artifacts: readonly DemandArtifactRead[];
}

function descricaoDaVersaoCorrente(artifact: DemandArtifactRead): string {
  const corrente = artifact.versions.at(-1);

  if (corrente === undefined) {
    return 'Sem versao registrada.';
  }

  return `Versao ${corrente.number} (${rotuloDaOrigem(corrente.origin)}) em ${formatarDataHora(
    corrente.created_at,
  )}.`;
}

export function DemandDetailArtifacts({ artifacts }: DemandDetailArtifactsProps) {
  if (artifacts.length === 0) {
    return (
      <p className="demand-detail__empty">
        Nenhum artefato gerado ate agora. Eles aparecem conforme a demanda avanca pelas etapas.
      </p>
    );
  }

  return (
    <ul className="demand-detail__artifacts">
      {artifacts.map((artifact) => (
        <li key={artifact.id} className="demand-detail__artifact">
          <p className="demand-detail__artifact-title">
            <span className="tag">{rotuloDoTipoDeArtefato(artifact.type)}</span>{' '}
            {artifact.title ?? 'Sem titulo'}
          </p>
          <p className="demand-detail__artifact-meta">
            {descricaoDaVersaoCorrente(artifact)} Criado em {formatarDataHora(artifact.created_at)}.
          </p>
          <p className="demand-detail__artifact-meta">
            <Link to={buildPath.artifactVersions(artifact.id)}>
              Ver o historico de versoes ({artifact.versions.length})
            </Link>
          </p>
        </li>
      ))}
    </ul>
  );
}
