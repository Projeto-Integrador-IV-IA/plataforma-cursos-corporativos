/**
 * Tela central da demanda (RF02): contexto da negociacao, cliente, etapa
 * corrente, fontes e artefatos em um lugar so.
 *
 * Uma consulta so alimenta a tela inteira. `GET /api/v1/demands/{id}` devolve
 * o agregado `DemandDetail`, com cliente e artefatos aninhados - o contrato foi
 * desenhado assim justamente para esta tela nao abrir uma segunda chamada por
 * bloco.
 *
 * As secoes sao ancoras de verdade, nao abas: o conteudo inteiro fica no DOM e
 * o indice leva ate ele. Assim a leitura continua possivel com o teclado, a
 * busca do navegador acha o que esta fora da vista e nenhum bloco depende de
 * estado para existir.
 *
 * O que esta tela ainda nao faz, e por que:
 *  - etapa e situacao aparecem, mas nao mudam por aqui - quem as move e o
 *    pipeline (RF05, RF06), que registra a transicao e ainda nao tem operacao
 *    publicada no contrato;
 *  - as fontes captadas chegam no agregado da demanda e aparecem nesta tela.
 */

import { useQuery } from "@tanstack/react-query";
import { type ReactNode, useState } from "react";
import { Link, useSearchParams } from "react-router-dom";

import { buildPath, QUERY_PARAMS } from "@/app/paths";
import { DemandDetailArtifacts } from "@/features/demands/DemandDetailArtifacts";
import { DemandDetailContextForm } from "@/features/demands/DemandDetailContextForm";
import {
  formatarDataHora,
  ouSemInformacao,
  rotuloDaEtapa,
  rotuloDaSituacao,
} from "@/features/demands/DemandDetailLabels";
import { demandDetailKey } from "@/features/demands/DemandDetailQueryKeys";
import { DemandDetailSources } from "@/features/demands/DemandDetailSources";
import { DemandStructuringStatus } from "@/features/demands/DemandStructuringStatus";
import { isApiError } from "@/services/api";
import { getDemand } from "@/services/demands";
import type { DemandRawInputRead, Uuid } from "@/types/api";

/** Mensagem exibida quando a falha nao veio no envelope da plataforma. */
const FALHA_GENERICA = "Nao foi possivel carregar a demanda. Tente novamente.";

/** Indice da tela. A ordem e a da leitura: o que foi pedido, por quem, onde esta. */
const SECOES: readonly { readonly id: string; readonly titulo: string }[] = [
  { id: "demanda-contexto", titulo: "Contexto" },
  { id: "demanda-cliente", titulo: "Cliente" },
  { id: "demanda-etapa", titulo: "Etapa e situacao" },
  { id: "demanda-curso-ia", titulo: "Curso com IA" },
  { id: "demanda-fontes", titulo: "Fontes captadas" },
  { id: "demanda-artefatos", titulo: "Artefatos" },
];

function mensagemDeErro(erro: unknown): string {
  return isApiError(erro) ? erro.message : FALHA_GENERICA;
}

function fonteMaisRecente(
  fontes: readonly DemandRawInputRead[],
): DemandRawInputRead | undefined {
  return fontes.reduce<DemandRawInputRead | undefined>(
    (maisRecente, fonte) =>
      maisRecente === undefined || new Date(fonte.created_at) > new Date(maisRecente.created_at)
        ? fonte
        : maisRecente,
    undefined,
  );
}

interface CampoProps {
  termo: string;
  children: ReactNode;
}

/** Par rotulo/valor dos blocos de leitura. */
function Campo({ termo, children }: CampoProps) {
  return (
    <div className="demand-detail__field">
      <dt className="demand-detail__term">{termo}</dt>
      <dd className="demand-detail__value">{children}</dd>
    </div>
  );
}

interface DemandDetailViewProps {
  demandId: Uuid;
}

export function DemandDetailView({ demandId }: DemandDetailViewProps) {
  const [editandoContexto, setEditandoContexto] = useState(false);
  const [searchParams] = useSearchParams();
  const execucao = searchParams.get(QUERY_PARAMS.structuringJob);
  const caminhoDaRevisao = `${buildPath.demandStructuring(demandId)}${
    execucao === null
      ? ""
      : `?${QUERY_PARAMS.structuringJob}=${encodeURIComponent(execucao)}`
  }`;

  const detalhe = useQuery({
    queryKey: demandDetailKey(demandId),
    queryFn: ({ signal }) => getDemand(demandId, { signal }),
    enabled: demandId !== "",
  });

  if (detalhe.isPending) {
    return (
      <p className="page__pending" aria-live="polite">
        Carregando a demanda…
      </p>
    );
  }

  if (detalhe.isError) {
    return (
      <p className="demand-detail__failure" aria-live="polite">
        {mensagemDeErro(detalhe.error)}
      </p>
    );
  }

  const demanda = detalhe.data;
  const cliente = demanda.client;

  return (
    <div className="demand-detail">
      <header className="demand-detail__hero">
        <div>
          <p className="demand-detail__eyebrow">NEGOCIAÇÃO</p>
          <h2 className="demand-detail__headline">{demanda.title}</h2>
          <p className="demand-detail__hero-client">{cliente.name}</p>
        </div>
        <p className="demand-detail__tags">
          <span className="tag demand-detail__stage">
            {rotuloDaEtapa(demanda.current_stage)}
          </span>
          <span className="tag">{rotuloDaSituacao(demanda.status)}</span>
        </p>
      </header>

      <nav className="demand-detail__index" aria-label="Secoes da demanda">
        <ul className="demand-detail__index-list">
          {SECOES.map((secao) => (
            <li key={secao.id}>
              <a href={`#${secao.id}`}>{secao.titulo}</a>
            </li>
          ))}
        </ul>
      </nav>

      <section
        className="demand-detail__section demand-detail__section--context"
        aria-labelledby="demanda-contexto"
      >
        <h2 className="demand-detail__section-title" id="demanda-contexto">
          Contexto
        </h2>
        {editandoContexto ? (
          <DemandDetailContextForm
            demand={demanda}
            onFinish={() => setEditandoContexto(false)}
          />
        ) : (
          <>
            <dl className="demand-detail__fields">
              <Campo termo="Titulo">{demanda.title}</Campo>
              <Campo termo="Contexto">
                {ouSemInformacao(demanda.description)}
              </Campo>
              <Campo termo="Responsavel">
                {demanda.owner_id ?? "Sem responsavel definido"}
              </Campo>
            </dl>
            <div className="form__actions demand-detail__actions">
              <button
                className="button"
                type="button"
                onClick={() => setEditandoContexto(true)}
              >
                Editar contexto
              </button>
            </div>
          </>
        )}
      </section>

      <section
        className="demand-detail__section demand-detail__section--client"
        aria-labelledby="demanda-cliente"
      >
        <h2 className="demand-detail__section-title" id="demanda-cliente">
          Cliente
        </h2>
        <dl className="demand-detail__fields">
          <Campo termo="Empresa">
            <Link to={buildPath.clientDetail(cliente.id)}>{cliente.name}</Link>
          </Campo>
          <Campo termo="CNPJ">{ouSemInformacao(cliente.cnpj)}</Campo>
          <Campo termo="Segmento">{ouSemInformacao(cliente.segment)}</Campo>
          <Campo termo="Contato">{ouSemInformacao(cliente.contact_name)}</Campo>
          <Campo termo="E-mail">{ouSemInformacao(cliente.contact_email)}</Campo>
          <Campo termo="Telefone">
            {ouSemInformacao(cliente.contact_phone)}
          </Campo>
          <Campo termo="Situacao do cadastro">
            {cliente.active ? "Ativo" : "Inativo"}
          </Campo>
        </dl>
        {cliente.notes === null ? null : (
          <p className="page__description">
            Observacoes do cadastro: {cliente.notes}
          </p>
        )}
      </section>

      <section
        className="demand-detail__section demand-detail__section--stage"
        aria-labelledby="demanda-etapa"
      >
        <h2 className="demand-detail__section-title" id="demanda-etapa">
          Etapa e situacao
        </h2>
        <dl className="demand-detail__fields">
          <Campo termo="Etapa corrente">
            {rotuloDaEtapa(demanda.current_stage)}
          </Campo>
          <Campo termo="Situacao">{rotuloDaSituacao(demanda.status)}</Campo>
          <Campo termo="Aberta em">
            {formatarDataHora(demanda.created_at)}
          </Campo>
          <Campo termo="Ultima alteracao">
            {formatarDataHora(demanda.updated_at)}
          </Campo>
          <Campo termo="Identificador">{demanda.id}</Campo>
        </dl>
      </section>

      <section
        className="demand-detail__section demand-detail__section--ai"
        aria-labelledby="demanda-curso-ia"
      >
        <h2 className="demand-detail__section-title" id="demanda-curso-ia">
          Curso com IA
        </h2>
        <DemandStructuringStatus
          demandId={demandId}
          source={fonteMaisRecente(demanda.raw_inputs)}
        />
        <div className="demand-detail__actions">
          <Link
            className="button button--secondary"
            to={caminhoDaRevisao}
          >
            Ver curso e revisar
          </Link>
        </div>
      </section>

      <section
        className="demand-detail__section demand-detail__section--sources"
        aria-labelledby="demanda-fontes"
      >
        <h2 className="demand-detail__section-title" id="demanda-fontes">
          Fontes captadas
        </h2>
        <DemandDetailSources demandId={demandId} sources={demanda.raw_inputs} />
      </section>

      <section
        className="demand-detail__section demand-detail__section--artifacts"
        aria-labelledby="demanda-artefatos"
      >
        <h2 className="demand-detail__section-title" id="demanda-artefatos">
          Artefatos
        </h2>
        <DemandDetailArtifacts artifacts={demanda.artifacts} />
      </section>
    </div>
  );
}
