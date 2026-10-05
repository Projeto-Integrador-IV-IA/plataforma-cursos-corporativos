/**
 * Listagem paginada de demandas (RF03).
 *
 * Visao em lista do mesmo conteudo do pipeline: quem precisa varrer a carteira
 * inteira - "o que esta aberto na Industria Alfa?" - le melhor uma tabela do
 * que um quadro de cartoes.
 *
 * Ordenacao. O contrato de `GET /api/v1/demands` nao aceita parametro de
 * ordenacao: o servidor ordena sempre por `created_at DESC, id DESC`. Por isso
 * a URL carrega pagina e filtros, mas nao ordenacao. Ordenar no cliente seria
 * pior do que nao ordenar - reorganizaria apenas as 20 linhas da pagina
 * corrente, dando ao operador a impressao de uma ordem que a paginacao nao
 * respeita. A ordem fica dita em texto, na legenda da tabela, e a listagem a
 * mantem ao trocar de pagina porque quem ordena e o servidor. Quando o contrato
 * passar a aceitar ordenacao, ela entra na URL ao lado de `pagina`.
 *
 * Estado na URL. Pagina, situacao e cliente vivem em query string: o operador
 * volta pelo botao do navegador, recarrega a aba e envia o link da busca para
 * um colega sem perder o recorte. Trocar filtro volta para a primeira pagina,
 * senao a pagina 3 de um filtro vira uma lista vazia no filtro seguinte.
 *
 * Periodo (`from`/`to`) o contrato aceita e esta tela ainda nao oferece; entra
 * quando houver o controle de data definido.
 */

import { keepPreviousData, useQuery } from '@tanstack/react-query';
import { useId, useMemo } from 'react';
import { Link, useSearchParams } from 'react-router-dom';

import { PATHS } from '@/app/paths';
import { STATUS_LABELS } from '@/features/demands/DemandListLabels';
import { DemandListPager } from '@/features/demands/DemandListPager';
import { DemandListTable } from '@/features/demands/DemandListTable';
import { isApiError } from '@/services/api';
import { listClients } from '@/services/clients';
import { listDemands } from '@/services/demands';
import { DEMAND_STATUSES, type Client, type DemandStatus, type Uuid } from '@/types/api';

/** Demandas por pagina. O contrato admite ate 100; 20 e o padrao dele. */
const PAGE_SIZE = 20;

/** Quantos clientes a selecao e o mapa de nomes carregam de uma vez. */
const CLIENT_LIMIT = 100;

/**
 * Nomes dos parametros de busca. Ficam em portugues como as rotas
 * (`/demandas/nova`), porque URL e texto que o operador ve e compartilha.
 */
const PARAM = {
  page: 'pagina',
  status: 'situacao',
  client: 'cliente',
} as const;

const GENERIC_FAILURE = 'Nao foi possivel carregar as demandas. Tente novamente.';

function errorMessage(error: unknown): string {
  return isApiError(error) ? error.message : GENERIC_FAILURE;
}

function readPage(params: URLSearchParams): number {
  const raw = Number(params.get(PARAM.page));

  // Pagina invalida na URL nao e erro do operador: cai na primeira, que e
  // sempre uma resposta valida.
  return Number.isInteger(raw) && raw >= 1 ? raw : 1;
}

function readStatus(params: URLSearchParams): DemandStatus | undefined {
  const raw = params.get(PARAM.status);

  // Valor fora do contrato e descartado aqui, antes de virar um 422.
  return DEMAND_STATUSES.find((status) => status === raw);
}

function readClient(params: URLSearchParams): Uuid | undefined {
  const raw = params.get(PARAM.client);

  return raw === null || raw === '' ? undefined : raw;
}

function clientLabel(client: Client): string {
  return client.cnpj === null ? client.name : `${client.name} — ${client.cnpj}`;
}

export function DemandList() {
  const [searchParams, setSearchParams] = useSearchParams();

  const statusFieldId = useId();
  const clientFieldId = useId();

  const page = readPage(searchParams);
  const status = readStatus(searchParams);
  const clientId = readClient(searchParams);
  const filtered = status !== undefined || clientId !== undefined;

  const params = useMemo(
    () => ({
      limit: PAGE_SIZE,
      offset: (page - 1) * PAGE_SIZE,
      status,
      client_id: clientId,
    }),
    [page, status, clientId],
  );

  const demands = useQuery({
    queryKey: ['demands', params],
    queryFn: ({ signal }) => listDemands(params, { signal }),
    // Mantem a pagina anterior na tela enquanto a proxima chega: a tabela nao
    // pisca em branco a cada clique no paginador.
    placeholderData: keepPreviousData,
  });

  const clients = useQuery({
    queryKey: ['clients', { size: CLIENT_LIMIT }],
    queryFn: ({ signal }) => listClients({ size: CLIENT_LIMIT }, { signal }),
  });

  const clientNames = useMemo(() => {
    const names = new Map<Uuid, string>();

    for (const client of clients.data?.items ?? []) {
      names.set(client.id, client.name);
    }

    return names;
  }, [clients.data]);

  /** Aplica mudancas na query string; valor vazio remove o parametro. */
  function changeSearch(changes: Readonly<Record<string, string>>) {
    setSearchParams((current) => {
      const next = new URLSearchParams(current);

      for (const [key, value] of Object.entries(changes)) {
        if (value === '') {
          next.delete(key);
        } else {
          next.set(key, value);
        }
      }

      return next;
    });
  }

  function handleFilterChange(key: string, value: string) {
    changeSearch({ [key]: value, [PARAM.page]: '' });
  }

  function clearFilters() {
    changeSearch({ [PARAM.status]: '', [PARAM.client]: '', [PARAM.page]: '' });
  }

  const total = demands.data?.total ?? 0;
  const totalPages = Math.max(1, Math.ceil(total / PAGE_SIZE));
  const items = demands.data?.items ?? [];

  return (
    <section className="demand-list">
      <form
        className="demand-list__filters"
        aria-label="Filtros da lista de demandas"
        onSubmit={(event) => event.preventDefault()}
      >
        <div className="form__field">
          <label className="form__label" htmlFor={statusFieldId}>
            Situacao
          </label>
          <select
            id={statusFieldId}
            className="form__control"
            value={status ?? ''}
            onChange={(event) => handleFilterChange(PARAM.status, event.target.value)}
          >
            <option value="">Todas</option>
            {DEMAND_STATUSES.map((value) => (
              <option key={value} value={value}>
                {STATUS_LABELS[value]}
              </option>
            ))}
          </select>
        </div>

        <div className="form__field">
          <label className="form__label" htmlFor={clientFieldId}>
            Cliente
          </label>
          <select
            id={clientFieldId}
            className="form__control"
            value={clientId ?? ''}
            disabled={clients.isPending || clients.isError}
            onChange={(event) => handleFilterChange(PARAM.client, event.target.value)}
          >
            <option value="">Todos</option>
            {(clients.data?.items ?? []).map((client) => (
              <option key={client.id} value={client.id}>
                {clientLabel(client)}
              </option>
            ))}
          </select>
        </div>
      </form>

      {clients.isError ? (
        <p className="form__hint form__hint--error" role="status">
          {errorMessage(clients.error)} As demandas continuam listadas, com o identificador do
          cliente no lugar do nome.
        </p>
      ) : null}

      {demands.isPending ? (
        <p className="demand-list__state" role="status">
          Carregando demandas…
        </p>
      ) : null}

      {demands.isError ? (
        <div className="demand-list__state demand-list__state--error" role="alert">
          <p>{errorMessage(demands.error)}</p>
          <button type="button" className="button" onClick={() => void demands.refetch()}>
            Tentar novamente
          </button>
        </div>
      ) : null}

      {demands.isSuccess && items.length === 0 ? (
        <div className="demand-list__state" role="status">
          {filtered ? (
            <>
              <p>Nenhuma demanda atende a este filtro.</p>
              <button type="button" className="button" onClick={clearFilters}>
                Limpar filtros
              </button>
            </>
          ) : (
            <p>
              Nenhuma demanda aberta ate agora.{' '}
              <Link to={PATHS.demandNew}>Abra a primeira negociacao</Link>.
            </p>
          )}
        </div>
      ) : null}

      {demands.isSuccess && items.length > 0 ? (
        <>
          <DemandListTable demands={items} clientNames={clientNames} />
          <DemandListPager
            page={page}
            totalPages={totalPages}
            total={total}
            loading={demands.isFetching}
            onPageChange={(next) => changeSearch({ [PARAM.page]: String(next) })}
          />
        </>
      ) : null}
    </section>
  );
}
