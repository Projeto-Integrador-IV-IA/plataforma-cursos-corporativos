/**
 * Tabela de demandas (RF03).
 *
 * Tabela de dados de verdade, nao um desenho de linhas: `caption` diz o que a
 * lista contem e em que ordem, cada coluna tem `th scope="col"` e o titulo da
 * demanda e o `th scope="row"` da linha. Um leitor de tela anuncia "Cliente:
 * Industria Alfa" ao andar pelas celulas, em vez de ler seis valores soltos.
 * A navegacao por teclado sai dai: o unico elemento interativo da linha e o
 * link do titulo, que ja entra na ordem natural de tabulacao.
 *
 * Nome do cliente: `DemandRead` so traz `client_id`, entao quem monta a tela
 * carrega os clientes a parte e passa o mapa `id -> nome` por aqui. Quando o id
 * nao esta no mapa - lista de clientes indisponivel, ou cliente fora do recorte
 * carregado - a celula mostra o inicio do identificador, que ainda permite
 * conferir a demanda, em vez de mentir um nome ou deixar a celula vazia.
 *
 * Responsavel: nao existe endpoint que liste usuarios, entao nao ha de onde
 * tirar o nome. A coluna exibe "Nao atribuido" quando `owner_id` e nulo e o
 * identificador abreviado quando nao e - o dado que o contrato entrega hoje,
 * sem simular o que ele nao entrega. Com a autenticacao (RF16) o nome substitui
 * o identificador.
 */

import { Link } from 'react-router-dom';

import { buildPath } from '@/app/paths';
import { STAGE_LABELS, STATUS_LABELS } from '@/features/demands/DemandListLabels';
import type { DemandRead, IsoDateTime, Uuid } from '@/types/api';

/** Quantos caracteres do UUID bastam para diferenciar registros na tela. */
const ID_PREFIX_LENGTH = 8;

const DATE_FORMAT = new Intl.DateTimeFormat('pt-BR', { dateStyle: 'short' });

function formatDate(value: IsoDateTime): string {
  const parsed = new Date(value);

  // Data ilegivel nao derruba a linha: mostra-se o valor cru, que ao menos
  // permite reportar o problema com o dado em maos.
  return Number.isNaN(parsed.getTime()) ? value : DATE_FORMAT.format(parsed);
}

function shortId(id: Uuid): string {
  return id.slice(0, ID_PREFIX_LENGTH);
}

interface DemandListTableProps {
  readonly demands: readonly DemandRead[];
  /** Nome do cliente por identificador, montado por quem carrega a lista. */
  readonly clientNames: ReadonlyMap<Uuid, string>;
}

export function DemandListTable({ demands, clientNames }: DemandListTableProps) {
  return (
    <table className="demand-table">
      <caption className="demand-table__caption">
        Demandas por data de criacao, da mais recente para a mais antiga.
      </caption>
      <thead>
        <tr>
          <th scope="col">Demanda</th>
          <th scope="col">Cliente</th>
          <th scope="col">Etapa corrente</th>
          <th scope="col">Situacao</th>
          <th scope="col">Responsavel</th>
          <th scope="col">Criada em</th>
        </tr>
      </thead>
      <tbody>
        {demands.map((demand) => {
          const clientName = clientNames.get(demand.client_id);

          return (
            <tr key={demand.id}>
              <th scope="row" className="demand-table__demand">
                <Link to={buildPath.demandDetail(demand.id)}>{demand.title}</Link>
              </th>
              <td>
                {clientName === undefined ? (
                  <abbr
                    className="demand-table__muted"
                    title={`Identificador do cliente: ${demand.client_id}`}
                  >
                    {shortId(demand.client_id)}
                  </abbr>
                ) : (
                  clientName
                )}
              </td>
              <td>
                <span className="demand-table__stage">{STAGE_LABELS[demand.current_stage]}</span>
              </td>
              <td>
                <span
                  className={`demand-table__status demand-table__status--${demand.status.toLowerCase()}`}
                >
                  {STATUS_LABELS[demand.status]}
                </span>
              </td>
              <td>
                {demand.owner_id === null ? (
                  <span className="demand-table__muted">Nao atribuido</span>
                ) : (
                  <abbr
                    className="demand-table__muted"
                    title={`Identificador do responsavel: ${demand.owner_id}`}
                  >
                    {shortId(demand.owner_id)}
                  </abbr>
                )}
              </td>
              <td>
                <time dateTime={demand.created_at}>{formatDate(demand.created_at)}</time>
              </td>
            </tr>
          );
        })}
      </tbody>
    </table>
  );
}
