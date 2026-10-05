/**
 * Tabela de clientes (RF03).
 *
 * Mesma forma acessivel da tabela de demandas, pela mesma razao: `caption`
 * dizendo o que a lista contem e em que ordem, `th scope="col"` em cada coluna
 * e o nome do cliente como `th scope="row"` da linha. Quem usa leitor de tela
 * ouve "Segmento: Metalurgia" ao andar pelas celulas, em vez de seis valores
 * soltos, e o unico elemento focavel da linha e o link do nome, que ja entra na
 * ordem natural de tabulacao.
 *
 * A legenda declara a ordem porque a URL nao pode declarar: o contrato de
 * `GET /api/v1/clients` nao aceita parametro de ordenacao e o servico ordena
 * sempre por `created_at DESC, id ASC`.
 *
 * Campo opcional em branco vira "Nao informado" visivel, e nao celula vazia:
 * celula vazia e ambigua entre "nao ha dado" e "a tela falhou ao mostra-lo", e
 * o cadastro (RF01) so exige o nome, entao a ausencia e o caso comum.
 */

import { Link } from 'react-router-dom';

import { buildPath } from '@/app/paths';
import type { Client, IsoDateTime } from '@/types/api';

const DATE_FORMAT = new Intl.DateTimeFormat('pt-BR', { dateStyle: 'short' });

function formatDate(value: IsoDateTime): string {
  const parsed = new Date(value);

  // Data ilegivel nao derruba a linha: mostra-se o valor cru, que ao menos
  // permite reportar o problema com o dado em maos.
  return Number.isNaN(parsed.getTime()) ? value : DATE_FORMAT.format(parsed);
}

/** Valor opcional do cadastro, ou o aviso de que ele nao foi preenchido. */
function OptionalCell({ value }: { readonly value: string | null }) {
  if (value === null || value.trim() === '') {
    return <span className="client-table__muted">Nao informado</span>;
  }

  return <>{value}</>;
}

interface ClientListTableProps {
  readonly clients: readonly Client[];
}

export function ClientListTable({ clients }: ClientListTableProps) {
  return (
    <table className="client-table">
      <caption className="client-table__caption">
        Clientes por data de cadastro, do mais recente para o mais antigo.
      </caption>
      <thead>
        <tr>
          <th scope="col">Cliente</th>
          <th scope="col">CNPJ</th>
          <th scope="col">Segmento</th>
          <th scope="col">Contato</th>
          <th scope="col">Situacao</th>
          <th scope="col">Cadastrado em</th>
        </tr>
      </thead>
      <tbody>
        {clients.map((client) => (
          <tr key={client.id}>
            <th scope="row" className="client-table__client">
              <Link to={buildPath.clientDetail(client.id)}>{client.name}</Link>
            </th>
            <td>
              <OptionalCell value={client.cnpj} />
            </td>
            <td>
              <OptionalCell value={client.segment} />
            </td>
            <td>
              <OptionalCell value={client.contact_name} />
            </td>
            <td>
              <span
                className={`client-table__status client-table__status--${
                  client.active ? 'ativo' : 'inativo'
                }`}
              >
                {client.active ? 'Ativo' : 'Inativo'}
              </span>
            </td>
            <td>
              <time dateTime={client.created_at}>{formatDate(client.created_at)}</time>
            </td>
          </tr>
        ))}
      </tbody>
    </table>
  );
}
