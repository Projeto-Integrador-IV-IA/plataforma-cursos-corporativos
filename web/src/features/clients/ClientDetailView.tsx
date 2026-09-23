/**
 * Cadastro de uma empresa cliente e as demandas dela (RF01; RF01.2 no
 * Documento Consolidado v1.0).
 *
 * E onde o operador confere e corrige o cadastro antes de abrir demandas: o
 * bloco de dados alterna entre leitura e edicao, e a edicao vai por
 * `PATCH /api/v1/clients/{client_id}`, que devolve o cadastro ja atualizado -
 * por isso a tela escreve a resposta no cache em vez de esperar a releitura.
 *
 * Identificador inexistente nao e falha da tela: o contrato responde 404 com o
 * envelope de erro da plataforma, e aqui isso vira um estado de vazio com o
 * caminho de volta para a listagem, nao uma mensagem de erro vermelha.
 *
 * O que esta tela nao faz, e por que:
 *  - nao ativa nem inativa o cliente: a inativacao e operacao propria (RF01.3)
 *    e o `PATCH` de cadastro recusa o campo `active`;
 *  - nao filtra nem pagina as demandas: isso e da tela de demandas (RF03), e o
 *    bloco daqui so mostra as primeiras com o caminho para a listagem.
 */

import { useQuery } from '@tanstack/react-query';
import { type ReactNode, useState } from 'react';
import { Link } from 'react-router-dom';

import { PATHS } from '@/app/paths';
import { ClientDetailDemands } from '@/features/clients/ClientDetailDemands';
import { ClientDetailForm } from '@/features/clients/ClientDetailForm';
import { clientDetailKey } from '@/features/clients/ClientDetailQueryKeys';
import { formatarDataHora, ouSemInformacao } from '@/features/demands/DemandDetailLabels';
import { isApiError } from '@/services/api';
import { getClient } from '@/services/clients';
import type { Uuid } from '@/types/api';

/** Mensagem exibida quando a falha nao veio no envelope da plataforma. */
const FALHA_GENERICA = 'Nao foi possivel carregar o cliente. Tente novamente.';

function mensagemDeErro(erro: unknown): string {
  return isApiError(erro) ? erro.message : FALHA_GENERICA;
}

/** Cliente inexistente: o contrato responde 404 nesta consulta. */
function ehInexistente(erro: unknown): boolean {
  return isApiError(erro) && erro.status === 404;
}

interface CampoProps {
  termo: string;
  children: ReactNode;
}

/** Par rotulo/valor do bloco de leitura. */
function Campo({ termo, children }: CampoProps) {
  return (
    <div className="client-detail__field">
      <dt className="client-detail__term">{termo}</dt>
      <dd className="client-detail__value">{children}</dd>
    </div>
  );
}

interface ClientDetailViewProps {
  clientId: Uuid;
}

export function ClientDetailView({ clientId }: ClientDetailViewProps) {
  const [editando, setEditando] = useState(false);

  const detalhe = useQuery({
    queryKey: clientDetailKey(clientId),
    queryFn: ({ signal }) => getClient(clientId, { signal }),
    enabled: clientId !== '',
  });

  if (detalhe.isPending) {
    return (
      <p className="page__pending" aria-live="polite">
        Carregando o cliente…
      </p>
    );
  }

  if (detalhe.isError) {
    if (ehInexistente(detalhe.error)) {
      return (
        <div className="client-detail__empty" aria-live="polite">
          <p>Nenhum cliente cadastrado com este identificador.</p>
          <p>
            Ele pode ter sido removido, ou o endereco foi digitado errado.{' '}
            <Link to={PATHS.clients}>Voltar para a lista de clientes</Link>
          </p>
        </div>
      );
    }

    return (
      <p className="client-detail__failure" aria-live="polite">
        {mensagemDeErro(detalhe.error)}
      </p>
    );
  }

  const cliente = detalhe.data;

  return (
    <div className="client-detail">
      <p className="client-detail__headline">{cliente.name}</p>
      <p className="client-detail__tags">
        <span className="tag">{cliente.active ? 'Ativo' : 'Inativo'}</span>
        {cliente.segment === null ? null : <span className="tag">{cliente.segment}</span>}
      </p>

      <section className="client-detail__section" aria-labelledby="cliente-cadastro">
        <h2 className="client-detail__section-title" id="cliente-cadastro">
          Dados cadastrais
        </h2>
        {editando ? (
          <ClientDetailForm client={cliente} onFinish={() => setEditando(false)} />
        ) : (
          <>
            <dl className="client-detail__fields">
              <Campo termo="Razao social">{cliente.name}</Campo>
              <Campo termo="CNPJ">{ouSemInformacao(cliente.cnpj)}</Campo>
              <Campo termo="Segmento">{ouSemInformacao(cliente.segment)}</Campo>
              <Campo termo="Nome do contato">{ouSemInformacao(cliente.contact_name)}</Campo>
              <Campo termo="E-mail do contato">{ouSemInformacao(cliente.contact_email)}</Campo>
              <Campo termo="Telefone do contato">{ouSemInformacao(cliente.contact_phone)}</Campo>
              <Campo termo="Observacoes">{ouSemInformacao(cliente.notes)}</Campo>
              <Campo termo="Situacao do cadastro">{cliente.active ? 'Ativo' : 'Inativo'}</Campo>
              <Campo termo="Cadastrado em">{formatarDataHora(cliente.created_at)}</Campo>
              <Campo termo="Ultima alteracao">{formatarDataHora(cliente.updated_at)}</Campo>
            </dl>
            <div className="form__actions">
              <button className="button" type="button" onClick={() => setEditando(true)}>
                Editar cadastro
              </button>
            </div>
            {/* TODO(RF01.3): inativar o cliente daqui quando a operacao propria
                for publicada. O PATCH de cadastro nao aceita `active`. */}
            <p className="client-detail__note">
              Inativar o cliente ainda nao e possivel por esta tela: a operacao pertence ao RF01.3
              e nao foi publicada no contrato.
            </p>
          </>
        )}
      </section>

      <section className="client-detail__section" aria-labelledby="cliente-demandas">
        <h2 className="client-detail__section-title" id="cliente-demandas">
          Demandas do cliente
        </h2>
        <ClientDetailDemands clientId={cliente.id} />
      </section>
    </div>
  );
}
