/**
 * Quadro do pipeline: as demandas distribuidas pelas etapas (RF05).
 *
 * E a visao que da nome ao produto. A listagem (RF03) responde "o que existe
 * na carteira"; o quadro responde "onde tudo esta parado", numa consulta so -
 * `GET /api/v1/pipeline` devolve as cinco etapas, cada uma com seus cartoes e
 * o total real da etapa.
 *
 * Ordem das colunas. E a ordem em que o servico devolve as etapas. A interface
 * nao reordena nem monta as colunas a partir de uma lista propria de etapas: a
 * sequencia do pipeline e regra de negocio do pipeline-service, e uma segunda
 * copia dela aqui divergiria no dia em que uma etapa entrasse ou mudasse de
 * lugar. O quadro desenha o que recebe, inclusive a etapa vazia, que o
 * contrato garante que vem sempre.
 *
 * Rolagem. As cinco colunas nao cabem em tela estreita, e a rolagem horizontal
 * fica contida em `.pipeline-board__viewport`: o corpo da pagina nunca rola
 * para o lado, entao cabecalho e navegacao permanecem no lugar enquanto o
 * operador varre as etapas. A area rolavel e focalizavel (`tabIndex`) de
 * proposito - area que so rola com o mouse e inalcancavel por teclado.
 *
 * Movimentacao de etapa nao e desta tela. Arrastar o cartao (card #95) e
 * avancar/retroceder com justificativa (card #96) dependem das operacoes de
 * transicao, que ainda nao estao publicadas no contrato (RF06, RF07).
 *
 * Filtros. O endpoint aceita os mesmos da listagem (cliente, responsavel,
 * situacao, periodo) e o quadro ainda nao os oferece: o recorte entra junto
 * com o controle de filtros, para nascer com estado na URL como na listagem de
 * demandas, e nao como estado local que o operador nao consegue compartilhar.
 */

import { useQuery } from '@tanstack/react-query';
import { Link } from 'react-router-dom';

import { PATHS } from '@/app/paths';
import { demandCount } from '@/features/pipeline/PipelineBoardLabels';
import { PipelineStageColumn } from '@/features/pipeline/PipelineStageColumn';
import { isApiError } from '@/services/api';
import { getPipelineBoard } from '@/services/pipeline';
import type { PipelineBoardParams } from '@/types/api';

/**
 * Cartoes carregados por coluna. E o padrao do contrato, declarado aqui para
 * a tela poder dizer ao operador que o recorte existe.
 */
const CARDS_PER_STAGE = 20;

const BOARD_PARAMS: PipelineBoardParams = { limit: CARDS_PER_STAGE };

const GENERIC_FAILURE = 'Nao foi possivel carregar o pipeline. Tente novamente.';

function errorMessage(error: unknown): string {
  return isApiError(error) ? error.message : GENERIC_FAILURE;
}

export function PipelineBoardView() {
  const board = useQuery({
    queryKey: ['pipeline', 'board', BOARD_PARAMS],
    queryFn: ({ signal }) => getPipelineBoard(BOARD_PARAMS, { signal }),
  });

  return (
    <section className="pipeline-board">
      {board.isPending ? (
        <p className="pipeline-board__state" aria-live="polite">
          Carregando o pipeline…
        </p>
      ) : null}

      {board.isError ? (
        <div className="pipeline-board__state pipeline-board__state--error" aria-live="assertive">
          <p>{errorMessage(board.error)}</p>
          <button type="button" className="button" onClick={() => void board.refetch()}>
            Tentar novamente
          </button>
        </div>
      ) : null}

      {board.isSuccess ? (
        <>
          {board.data.total === 0 ? (
            <p className="pipeline-board__state" aria-live="polite">
              Nenhuma demanda no pipeline ate agora.{' '}
              <Link to={PATHS.demandNew}>Abra a primeira negociacao</Link>.
            </p>
          ) : null}

          {/*
           * `tabIndex` sem controle interativo proprio existe para o teclado
           * alcancar a rolagem; o rotulo diz o que a area contem e que ela rola
           * na horizontal.
           */}
          <div
            className="pipeline-board__viewport"
            role="group"
            aria-label="Etapas do pipeline, com rolagem horizontal"
            tabIndex={0}
          >
            <ol className="pipeline-board__columns">
              {board.data.stages.map((group) => (
                <PipelineStageColumn key={group.stage} group={group} />
              ))}
            </ol>
          </div>

          <p className="pipeline-board__summary" aria-live="polite">
            {demandCount(board.data.total)} no pipeline. Cada coluna carrega ate{' '}
            {CARDS_PER_STAGE} cartoes; o numero no topo da coluna e o total da etapa.{' '}
            <Link to={PATHS.demands}>Ver tudo em lista</Link>
          </p>
        </>
      ) : null}
    </section>
  );
}
