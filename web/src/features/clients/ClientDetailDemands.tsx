/**
 * Demandas abertas para o cliente, dentro da tela de detalhe (RF01, RF03).
 *
 * Lista enxuta de proposito: `GET /api/v1/demands?client_id=...` ja filtra por
 * cliente, e aqui o operador so precisa reconhecer a negociacao e chegar nela.
 * Filtro, paginacao e estado na URL sao da tela de demandas - quem quiser isso
 * segue pelo link do rodape, que abre a listagem ja filtrada por este cliente.
 *
 * A consulta pede apenas as primeiras `LIMITE` demandas. O total volta no
 * envelope da pagina, entao a tela consegue dizer quantas ficaram de fora sem
 * carregar todas.
 */

import { useQuery } from '@tanstack/react-query';
import { Link } from 'react-router-dom';

import { buildPath, PATHS } from '@/app/paths';
import { clientDemandsKey } from '@/features/clients/ClientDetailQueryKeys';
import {
  formatarDataHora,
  rotuloDaEtapa,
  rotuloDaSituacao,
} from '@/features/demands/DemandDetailLabels';
import { isApiError } from '@/services/api';
import { listDemands } from '@/services/demands';
import type { Uuid } from '@/types/api';

/** Quantas demandas o bloco carrega. O resto fica na tela de demandas. */
const LIMITE = 10;

/** Mensagem exibida quando a falha nao veio no envelope da plataforma. */
const FALHA_GENERICA = 'Nao foi possivel carregar as demandas do cliente. Tente novamente.';

function mensagemDeErro(erro: unknown): string {
  return isApiError(erro) ? erro.message : FALHA_GENERICA;
}

interface ClientDetailDemandsProps {
  clientId: Uuid;
}

export function ClientDetailDemands({ clientId }: ClientDetailDemandsProps) {
  const demandas = useQuery({
    queryKey: clientDemandsKey(clientId),
    queryFn: ({ signal }) => listDemands({ client_id: clientId, limit: LIMITE }, { signal }),
  });

  // O nome do parametro acompanha o da listagem de demandas, que le o filtro
  // de cliente da propria URL.
  const listagemFiltrada = `${PATHS.demands}?cliente=${clientId}`;

  if (demandas.isPending) {
    return (
      <p className="page__pending" aria-live="polite">
        Carregando as demandas do cliente…
      </p>
    );
  }

  if (demandas.isError) {
    return (
      <p className="client-detail__failure" aria-live="polite">
        {mensagemDeErro(demandas.error)}
      </p>
    );
  }

  const { items, total } = demandas.data;

  if (items.length === 0) {
    return (
      <>
        <p className="client-detail__empty">
          Este cliente ainda nao tem demanda aberta.
        </p>
        <p className="page__description">
          <Link to={PATHS.demandNew}>Abrir a primeira demanda</Link>
        </p>
      </>
    );
  }

  return (
    <>
      <ul className="client-detail__demands">
        {items.map((demanda) => (
          <li className="client-detail__demand" key={demanda.id}>
            <Link to={buildPath.demandDetail(demanda.id)}>{demanda.title}</Link>
            <p className="client-detail__demand-meta">
              <span className="tag">{rotuloDaEtapa(demanda.current_stage)}</span>
              <span className="tag">{rotuloDaSituacao(demanda.status)}</span>
              <span>Aberta em {formatarDataHora(demanda.created_at)}</span>
            </p>
          </li>
        ))}
      </ul>
      <p className="page__description">
        {items.length < total
          ? `Mostrando ${items.length} de ${total} demandas. `
          : `${total} demanda(s) no total. `}
        <Link to={listagemFiltrada}>Ver as demandas deste cliente na listagem</Link>
      </p>
    </>
  );
}
