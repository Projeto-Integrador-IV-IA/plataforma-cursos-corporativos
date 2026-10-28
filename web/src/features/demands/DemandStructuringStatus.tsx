/**
 * Estado de processamento da estruturacao (RF24, RF17).
 *
 * A estruturacao e assincrona e pode levar dezenas de segundos. Sem indicador,
 * o operador nao sabe se clicou, se travou ou se terminou - e clica de novo,
 * gerando execucao duplicada e consumo de modelo em dobro. Por isso duas
 * coisas andam juntas aqui: o estado que o servico devolve e o bloqueio do
 * reenvio enquanto houver execucao em curso.
 *
 * O estado e consultado por identificador de execucao, que fica na query
 * string (`?execucao=`). Guardar o identificador na URL e o que faz a tela
 * sobreviver a um recarregamento: estado em memoria sumiria no F5 e o operador
 * voltaria a nao saber se ainda ha algo rodando.
 *
 * Reenvio bloqueado em quatro situacoes, todas pela mesma razao - nao criar
 * execucao duplicada:
 *  - o pedido anterior ainda esta sendo aceito;
 *  - a execucao acompanhada esta `PENDENTE` ou `PROCESSANDO`;
 *  - ha execucao na URL e o estado dela ainda nao chegou (nao se sabe se
 *    terminou);
 *  - a demanda nao tem nenhuma fonte captada - sem texto nao ha o que
 *    estruturar (RF09, RNF05).
 *
 * O texto enviado e o da fonte captada mais recente, como o contrato a
 * devolve. A copia sanitizada (RF10, `normalized_content`) seria a preferida,
 * mas nenhuma operacao publicada a expoe - quando expuser, e ela que entra
 * aqui.
 *
 * TODO(#107): consultar o estado periodicamente ate o desfecho. Hoje a
 * transicao aparece quando o operador pede para atualizar.
 */

import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';
import { Link, useSearchParams } from 'react-router-dom';

import { buildPath, QUERY_PARAMS } from '@/app/paths';
import { formatarDataHora } from '@/features/demands/DemandDetailLabels';
import {
  explicacaoDoEstado,
  formatarDuracao,
  marcaDoEstado,
  rotuloDaFonte,
  rotuloDoEstado,
} from '@/features/demands/DemandStructuringLabels';
import {
  demandArtifactsKey,
  structuringJobKey,
} from '@/features/demands/DemandStructuringQueryKeys';
import { useFeedback } from '@/hooks/useFeedback';
import { isApiError } from '@/services/api';
import { getStructuringJob, submitStructuringJob } from '@/services/structuring';
import type {
  DemandRawInputRead,
  StructuringJobAccepted,
  StructuringJobRead,
  StructuringRequest,
  Uuid,
} from '@/types/api';

/** Mensagens exibidas quando a falha nao veio no envelope da plataforma. */
const FALHA_NO_ENVIO = 'Nao foi possivel enviar a demanda para estruturacao. Tente novamente.';
const FALHA_NO_ESTADO = 'Nao foi possivel consultar o estado da execucao.';

function mensagemDeErro(erro: unknown, padrao: string): string {
  return isApiError(erro) ? erro.message : padrao;
}

/**
 * Estado inicial de uma execucao recem-aceita.
 *
 * E exatamente o que o aceite garante: a execucao existe, nada comecou e nao
 * ha resultado. Semear o cache com isso evita que a tela fique sem estado
 * nenhum entre o aceite e a primeira consulta.
 */
function estadoInicial(aceite: StructuringJobAccepted): StructuringJobRead {
  return {
    job_id: aceite.job_id,
    demand_id: aceite.demand_id,
    status: aceite.status,
    created_at: aceite.created_at,
    started_at: null,
    finished_at: null,
    total_elapsed_ms: null,
    result: null,
    execution: null,
    error: null,
  };
}

interface DemandStructuringStatusProps {
  demandId: Uuid;
  /** Fonte captada mais recente; `undefined` quando a demanda nao tem nenhuma. */
  source: DemandRawInputRead | undefined;
}

export function DemandStructuringStatus({ demandId, source }: DemandStructuringStatusProps) {
  const [searchParams, setSearchParams] = useSearchParams();
  const queryClient = useQueryClient();
  const { showSuccess, showError } = useFeedback();

  const jobId = searchParams.get(QUERY_PARAMS.structuringJob) ?? '';

  const execucao = useQuery({
    queryKey: structuringJobKey(jobId),
    queryFn: ({ signal }) => getStructuringJob(jobId, { signal }),
    enabled: jobId !== '',
  });

  const envio = useMutation({
    mutationFn: (payload: StructuringRequest) => submitStructuringJob(payload),
    onSuccess: (aceite) => {
      queryClient.setQueryData(structuringJobKey(aceite.job_id), estadoInicial(aceite));
      setSearchParams(
        (atual) => {
          const proximo = new URLSearchParams(atual);
          proximo.set(QUERY_PARAMS.structuringJob, aceite.job_id);

          return proximo;
        },
        { replace: true },
      );
      showSuccess('Estruturacao enviada. Acompanhe o estado nesta tela.');
    },
    onError: (erro: unknown) => showError(mensagemDeErro(erro, FALHA_NO_ENVIO)),
  });

  const estado = execucao.data?.status;
  const emCurso = estado === 'PENDENTE' || estado === 'PROCESSANDO';
  // Execucao na URL cujo estado ainda nao chegou: nao se sabe se terminou, e
  // na duvida o reenvio continua bloqueado.
  const estadoDesconhecido = jobId !== '' && execucao.data === undefined && !execucao.isError;
  const reenvioBloqueado = envio.isPending || emCurso || estadoDesconhecido;

  function enviar() {
    if (source === undefined || reenvioBloqueado) {
      return;
    }

    envio.mutate({ demand_id: demandId, text: source.original_content });
  }

  async function atualizar() {
    await execucao.refetch();
    // A estrutura aparece na tela quando o pipeline anexa o artefato (RF13):
    // reler os artefatos e o que faz o resultado da execucao concluida chegar
    // a secao de revisao.
    await queryClient.invalidateQueries({ queryKey: demandArtifactsKey(demandId) });
  }

  return (
    <div className="structuring-status">
      {execucao.data === undefined ? (
        <p className="demand-detail__empty">
          Nenhuma execucao acompanhada nesta tela. Envie a demanda para estruturacao ou abra o
          endereco com o identificador da execucao.
        </p>
      ) : (
        <>
          <p
            className={`structuring-status__state structuring-status__state--${execucao.data.status.toLowerCase()}`}
            role="status"
            aria-live="polite"
            aria-label="Estado da execucao"
          >
            <span className="structuring-status__mark" aria-hidden="true">
              {marcaDoEstado(execucao.data.status)}
            </span>
            <span>
              <strong className="structuring-status__name">
                {rotuloDoEstado(execucao.data.status)}
              </strong>{' '}
              — {explicacaoDoEstado(execucao.data.status)}
            </span>
          </p>
          <p className="structuring-status__meta">
            Execucao {execucao.data.job_id}, aceita em{' '}
            {formatarDataHora(execucao.data.created_at)}
            {execucao.data.finished_at === null
              ? '.'
              : `, encerrada em ${formatarDataHora(execucao.data.finished_at)}.`}
            {execucao.data.total_elapsed_ms === null
              ? ''
              : ` Tempo total: ${formatarDuracao(execucao.data.total_elapsed_ms)}.`}
          </p>
          {execucao.data.error === null ? null : (
            <p className="demand-detail__failure">
              {execucao.data.error.message} (codigo {execucao.data.error.code})
            </p>
          )}
        </>
      )}

      {execucao.isError ? (
        <p className="structuring-status__meta">
          {mensagemDeErro(execucao.error, FALHA_NO_ESTADO)} A execucao pode nao existir mais: o
          registro de execucoes nao sobrevive ao reinicio do servico, e a demanda captada, sim.
        </p>
      ) : null}

      {source === undefined ? (
        <>
          <p className="demand-detail__empty">
            Esta demanda nao tem nenhuma fonte captada. Sem o texto do cliente nao ha o que
            estruturar.
          </p>
          <p className="page__description">
            <Link to={buildPath.demandIngestion(demandId)}>Registrar uma fonte na captacao</Link>
          </p>
        </>
      ) : (
        <>
          <div className="form__actions">
            <button
              className="button"
              type="button"
              disabled={reenvioBloqueado}
              onClick={enviar}
            >
              {envio.isPending
                ? 'Enviando…'
                : jobId === ''
                  ? 'Estruturar com IA'
                  : 'Reenviar a estruturacao'}
            </button>
            <button
              className="button button--secondary"
              type="button"
              disabled={jobId === '' || execucao.isFetching}
              onClick={() => void atualizar()}
            >
              {execucao.isFetching ? 'Atualizando…' : 'Atualizar estado'}
            </button>
          </div>
          <p className="form__hint">
            {reenvioBloqueado
              ? 'Reenvio bloqueado enquanto houver execucao em curso: clicar de novo criaria uma segunda execucao da mesma demanda.'
              : `Texto enviado: a fonte captada mais recente (${rotuloDaFonte(source.source)}, ${formatarDataHora(source.created_at)}).`}
          </p>
        </>
      )}
    </div>
  );
}
