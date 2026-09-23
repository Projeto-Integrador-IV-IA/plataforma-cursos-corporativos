/**
 * Listagem paginada de clientes (RF03).
 *
 * Porta de entrada da navegacao: e daqui que se chega ao detalhe de um cliente
 * e, por ele, as demandas da conta.
 *
 * Ordenacao. O card pede pagina e ordenacao na URL, mas
 * `GET /api/v1/clients` nao aceita parametro de ordenacao - o servico ordena
 * sempre por `created_at DESC, id ASC`. Inventar `?ordem=` faria o link
 * compartilhado mentir: o proximo a abri-lo receberia a ordem do servidor com
 * a URL afirmando outra. Ordenar no cliente seria pior ainda, porque
 * reorganizaria so as 20 linhas desta pagina, sugerindo uma ordem que a
 * paginacao nao respeita. Entao a URL carrega o que o servidor honra - a
 * pagina - e a ordem fica dita em texto na legenda da tabela, mantida ao
 * trocar de pagina porque quem ordena e o servidor. E a mesma escolha feita na
 * listagem de demandas; quando o contrato aceitar ordenacao, ela entra na URL
 * ao lado de `pagina`, nas duas telas.
 *
 * Filtro. Tambem nao ha: o contrato desta operacao declara `page` e `size` e
 * nada mais. Busca por nome e recorte por ativos e desejavel nesta tela e
 * comeca em `packages/contracts/openapi/` (RNF02), nao aqui - um campo de busca
 * que filtrasse a pagina corrente pareceria varrer a base inteira.
 *
 * Estado na URL. A pagina vive na query string: o operador recarrega a aba,
 * volta pelo botao do navegador e manda o link a um colega sem voltar para a
 * primeira pagina.
 */

import { keepPreviousData, useQuery } from '@tanstack/react-query';
import { useMemo } from 'react';
import { Link, useSearchParams } from 'react-router-dom';

import { PATHS } from '@/app/paths';
import { ClientListPager } from '@/features/clients/ClientListPager';
import { ClientListTable } from '@/features/clients/ClientListTable';
import { isApiError } from '@/services/api';
import { listClients } from '@/services/clients';

/** Clientes por pagina. O contrato admite ate 100; 20 e o padrao dele. */
const PAGE_SIZE = 20;

/**
 * Nome do parametro de busca. Fica em portugues como as rotas
 * (`/clientes/novo`), porque URL e texto que o operador ve e compartilha.
 */
const PARAM = { page: 'pagina' } as const;

const GENERIC_FAILURE = 'Nao foi possivel carregar os clientes. Tente novamente.';

function errorMessage(error: unknown): string {
  return isApiError(error) ? error.message : GENERIC_FAILURE;
}

function readPage(params: URLSearchParams): number {
  const raw = Number(params.get(PARAM.page));

  // Pagina invalida na URL nao e erro do operador: cai na primeira, que e
  // sempre uma resposta valida.
  return Number.isInteger(raw) && raw >= 1 ? raw : 1;
}

export function ClientList() {
  const [searchParams, setSearchParams] = useSearchParams();

  const page = readPage(searchParams);

  const params = useMemo(() => ({ page, size: PAGE_SIZE }), [page]);

  const clients = useQuery({
    queryKey: ['clients', params],
    queryFn: ({ signal }) => listClients(params, { signal }),
    // Mantem a pagina anterior na tela enquanto a proxima chega: a tabela nao
    // pisca em branco a cada clique no paginador.
    placeholderData: keepPreviousData,
  });

  /** Leva a listagem para uma pagina; a primeira dispensa parametro na URL. */
  function goToPage(next: number) {
    setSearchParams((current) => {
      const search = new URLSearchParams(current);

      if (next <= 1) {
        search.delete(PARAM.page);
      } else {
        search.set(PARAM.page, String(next));
      }

      return search;
    });
  }

  const total = clients.data?.total ?? 0;
  const totalPages = Math.max(1, Math.ceil(total / PAGE_SIZE));
  const items = clients.data?.items ?? [];

  // Pagina vazia com cadastro existente e URL apontando alem do fim - link
  // antigo, ou cliente removido do recorte. A tela diz isso e oferece a volta,
  // em vez de repetir o convite ao primeiro cadastro.
  const beyondEnd = total > 0 && page > 1;

  return (
    <section className="client-list">
      {clients.isPending ? (
        <p className="client-list__state" aria-live="polite">
          Carregando clientes…
        </p>
      ) : null}

      {clients.isError ? (
        <div className="client-list__state client-list__state--error" aria-live="assertive">
          <p>{errorMessage(clients.error)}</p>
          <button type="button" className="button" onClick={() => void clients.refetch()}>
            Tentar novamente
          </button>
        </div>
      ) : null}

      {clients.isSuccess && items.length === 0 ? (
        <div className="client-list__state" aria-live="polite">
          {beyondEnd ? (
            <>
              <p>Esta pagina nao tem clientes.</p>
              <button type="button" className="button" onClick={() => goToPage(1)}>
                Voltar para a primeira pagina
              </button>
            </>
          ) : (
            <p>
              Nenhum cliente cadastrado ate agora.{' '}
              <Link to={PATHS.clientNew}>Cadastre o primeiro cliente</Link>.
            </p>
          )}
        </div>
      ) : null}

      {clients.isSuccess && items.length > 0 ? (
        <>
          <ClientListTable clients={items} />
          <ClientListPager
            page={page}
            totalPages={totalPages}
            total={total}
            loading={clients.isFetching}
            onPageChange={goToPage}
          />
        </>
      ) : null}
    </section>
  );
}
