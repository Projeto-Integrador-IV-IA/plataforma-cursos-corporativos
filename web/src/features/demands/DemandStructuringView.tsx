/**
 * Revisao humana da estrutura gerada pela IA (RF19, RF14).
 *
 * E aqui que a promessa do projeto se cumpre: a IA gera, a pessoa confere
 * antes de qualquer uso externo. Por isso a tela mostra a estrutura inteira,
 * com as fontes que a originaram, e nao oferece atalho nenhum para decidir sem
 * ler.
 *
 * Duas consultas, cada uma com um trabalho:
 *  - `GET /api/v1/demands/{id}` traz a negociacao e o texto das fontes
 *    captadas (`raw_inputs`), que e o que permite conferir campo a campo;
 *  - `GET /api/v1/demands/{id}/artifacts` traz o resultado anexado com o
 *    vinculo N:N das fontes que a IA usou - informacao que o agregado do
 *    detalhe nao carrega.
 *
 * A estrutura em revisao e a ultima versao do artefato `REQUISITOS_EXTRAIDOS`
 * mais recente: e o tipo com que o resultado estruturado e anexado a demanda
 * (RF13, `ArtifactResultCreate.type`). Versao e origem ficam visiveis porque a
 * revisao depende de saber o que se esta lendo - saida do modelo ou texto que
 * uma pessoa ja corrigiu.
 *
 * O que esta tela nao faz, e por que:
 *  - editar os campos e decidir sobre a estrutura sao cards proprios (#101 e
 *    #102), e cada um registra versao nova no artefato (RF08, RNF09);
 *  - nao ha "resultado parcial": enquanto nao existe artefato anexado, a tela
 *    diz isso em vez de exibir campos que ninguem preencheu.
 */

import { useQuery } from '@tanstack/react-query';
import { Link } from 'react-router-dom';

import { buildPath } from '@/app/paths';
import { formatarDataHora, rotuloDaOrigem } from '@/features/demands/DemandDetailLabels';
import { demandDetailKey } from '@/features/demands/DemandDetailQueryKeys';
import { DemandStructuringCourse } from '@/features/demands/DemandStructuringCourse';
import { demandArtifactsKey } from '@/features/demands/DemandStructuringQueryKeys';
import { DemandStructuringSources } from '@/features/demands/DemandStructuringSources';
import { lerCursoEstruturado } from '@/features/demands/StructuredCourseContent';
import { isApiError } from '@/services/api';
import { listArtifacts } from '@/services/artifacts';
import { getDemand } from '@/services/demands';
import type { ArtifactResultRead, ArtifactResultVersionRead, ArtifactType, Uuid } from '@/types/api';

/** Mensagem exibida quando a falha nao veio no envelope da plataforma. */
const FALHA_GENERICA = 'Nao foi possivel carregar a estrutura gerada. Tente novamente.';

/** Tipo com que o resultado estruturado e anexado a demanda (RF13). */
const TIPO_EM_REVISAO: ArtifactType = 'REQUISITOS_EXTRAIDOS';

function mensagemDeErro(erro: unknown): string {
  return isApiError(erro) ? erro.message : FALHA_GENERICA;
}

/** Artefato estruturado mais recente que ja tenha ao menos uma versao. */
function artefatoEmRevisao(
  artifacts: readonly ArtifactResultRead[],
): ArtifactResultRead | undefined {
  return artifacts
    .filter((artefato) => artefato.type === TIPO_EM_REVISAO && artefato.versions.length > 0)
    .reduce<ArtifactResultRead | undefined>((escolhido, candidato) => {
      if (escolhido === undefined) {
        return candidato;
      }

      return new Date(candidato.created_at) > new Date(escolhido.created_at)
        ? candidato
        : escolhido;
    }, undefined);
}

/** Versao corrente: a de maior numero, que e a que vale hoje (RF08). */
function versaoCorrente(artifact: ArtifactResultRead): ArtifactResultVersionRead | undefined {
  return artifact.versions.reduce<ArtifactResultVersionRead | undefined>(
    (escolhida, candidata) =>
      escolhida === undefined || candidata.number > escolhida.number ? candidata : escolhida,
    undefined,
  );
}

interface DemandStructuringViewProps {
  demandId: Uuid;
}

export function DemandStructuringView({ demandId }: DemandStructuringViewProps) {
  const demanda = useQuery({
    queryKey: demandDetailKey(demandId),
    queryFn: ({ signal }) => getDemand(demandId, { signal }),
    enabled: demandId !== '',
  });

  const artefatos = useQuery({
    queryKey: demandArtifactsKey(demandId),
    queryFn: ({ signal }) => listArtifacts(demandId, { signal }),
    enabled: demandId !== '',
  });

  if (demanda.isPending || artefatos.isPending) {
    return (
      <p className="page__pending" aria-live="polite">
        Carregando a estrutura gerada…
      </p>
    );
  }

  if (demanda.isError || artefatos.isError) {
    return (
      <p className="demand-detail__failure" aria-live="polite">
        {mensagemDeErro(demanda.error ?? artefatos.error)}
      </p>
    );
  }

  const artefato = artefatoEmRevisao(artefatos.data);
  const versao = artefato === undefined ? undefined : versaoCorrente(artefato);

  return (
    <div className="structuring">
      <p className="demand-detail__headline">{demanda.data.title}</p>
      <p className="demand-detail__tags">
        <span className="tag">{demanda.data.client.name}</span>
        {versao === undefined ? null : (
          <>
            <span className="tag">Versao {versao.number}</span>
            <span className="tag">Origem: {rotuloDaOrigem(versao.origin)}</span>
          </>
        )}
      </p>

      <section className="demand-detail__section" aria-labelledby="estrutura-gerada">
        <h2 className="demand-detail__section-title" id="estrutura-gerada">
          Estrutura gerada
        </h2>
        {artefato === undefined || versao === undefined ? (
          <p className="demand-detail__empty">
            Nenhuma estrutura foi anexada a esta demanda ate agora. Ela aparece aqui depois que a
            estruturacao por IA concluir.
          </p>
        ) : (
          <>
            <p className="structuring__meta">
              {artefato.title ?? 'Requisitos extraidos'}: versao {versao.number} (
              {rotuloDaOrigem(versao.origin)}) gerada em {formatarDataHora(versao.created_at)}.
            </p>
            <DemandStructuringCourse course={lerCursoEstruturado(versao.structured_content)} />
            <p className="page__description">
              <Link to={buildPath.artifactVersions(artefato.id)}>
                Ver o historico de versoes ({artefato.versions.length})
              </Link>
            </p>
          </>
        )}
      </section>

      <section className="demand-detail__section" aria-labelledby="estrutura-fontes">
        <h2 className="demand-detail__section-title" id="estrutura-fontes">
          Fontes de origem
        </h2>
        <DemandStructuringSources
          sources={artefato?.sources ?? []}
          rawInputs={demanda.data.raw_inputs}
          demandId={demandId}
        />
      </section>
    </div>
  );
}
