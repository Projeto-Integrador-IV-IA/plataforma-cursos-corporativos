/**
 * Fontes que originaram a estrutura em revisao (RF19, RNF09).
 *
 * Sem elas a revisao seria um ato de fe: o operador confirmaria "25
 * participantes" sem ter como saber de onde o numero saiu. O vinculo N:N do
 * artefato diz quais fontes a IA usou (`sources`) e o agregado da demanda traz
 * o texto de cada uma (`raw_inputs`) - o identificador liga os dois, e o texto
 * aparece integral, como foi captado (RNF05).
 *
 * O texto fica recolhido em `details` de proposito: a estrutura gerada e o
 * assunto da tela, e um e-mail inteiro aberto por padrao empurraria os campos
 * para fora da primeira tela. Recolhido ainda esta no DOM - a busca do
 * navegador o encontra e o teclado o alcanca.
 */

import { Link } from 'react-router-dom';

import { buildPath } from '@/app/paths';
import { formatarDataHora } from '@/features/demands/DemandDetailLabels';
import { rotuloDaFonte } from '@/features/demands/DemandStructuringLabels';
import type { ArtifactSourceRead, DemandRawInputRead, Uuid } from '@/types/api';

interface DemandStructuringSourcesProps {
  /** Fontes vinculadas ao artefato em revisao, como o contrato as devolve. */
  sources: readonly ArtifactSourceRead[];
  /** Fontes captadas da demanda, de onde sai o texto de cada uma. */
  rawInputs: readonly DemandRawInputRead[];
  demandId: Uuid;
}

export function DemandStructuringSources({
  sources,
  rawInputs,
  demandId,
}: DemandStructuringSourcesProps) {
  if (sources.length === 0) {
    return (
      <>
        <p className="demand-detail__empty">
          O artefato em revisao nao declara nenhuma fonte. Sem a procedencia, a estrutura nao pode
          ser conferida contra o que o cliente escreveu.
        </p>
        <p className="page__description">
          <Link to={buildPath.demandIngestion(demandId)}>Ver a captacao desta demanda</Link>
        </p>
      </>
    );
  }

  return (
    <>
      <ul className="structuring-sources">
        {sources.map((fonte) => {
          const captada = rawInputs.find((entrada) => entrada.id === fonte.id);

          return (
            <li className="structuring-sources__item" key={fonte.id}>
              <p className="structuring-sources__title">
                <span className="tag">{rotuloDaFonte(fonte.source)}</span> Captada em{' '}
                {formatarDataHora(fonte.created_at)}
              </p>
              {captada === undefined ? (
                <p className="structuring-sources__meta">
                  O texto desta fonte nao veio no detalhe da demanda. A referencia fica registrada:
                  identificador {fonte.id}.
                </p>
              ) : (
                <>
                  {captada.truncated ? (
                    <p className="structuring-sources__meta">
                      Texto cortado no limite de tamanho da captacao: a IA leu so o que esta aqui.
                    </p>
                  ) : null}
                  <details className="structuring-sources__text">
                    <summary>Ver o texto captado</summary>
                    <p className="structuring-sources__content">{captada.original_content}</p>
                  </details>
                </>
              )}
            </li>
          );
        })}
      </ul>
      <p className="page__description">
        <Link to={buildPath.demandIngestion(demandId)}>Ver a captacao desta demanda</Link>
      </p>
    </>
  );
}
