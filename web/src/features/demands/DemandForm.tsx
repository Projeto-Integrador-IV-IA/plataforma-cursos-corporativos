/**
 * Formulario de criacao de demanda (RF02).
 *
 * Segundo passo da demonstracao: com o cliente cadastrado, abre-se a
 * negociacao. O vinculo com cliente e obrigatorio no banco (RNF08), entao a
 * tela resolve o cliente antes de permitir o envio - sem cliente selecionado o
 * botao nao envia, e o operador nao descobre a obrigatoriedade por um erro 404
 * vindo do servidor.
 *
 * Situacao (`ABERTA`) e etapa inicial (`CAPTACAO`) sao definidas pelo servico e
 * nao aparecem aqui: quem move a demanda e o pipeline (RF05, RF06).
 *
 * Responsavel (`owner_id`): a API aceita, mas nao existe endpoint que liste
 * usuarios, e com a autenticacao (RF16) o responsavel provavelmente passa a ser
 * o usuario da sessao. Um campo de UUID livre seria descartado depois, entao o
 * controle fica de fora ate haver de onde escolher.
 */

import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';
import { type FormEvent, useId, useState } from 'react';
import { useNavigate } from 'react-router-dom';

import { buildPath } from '@/app/paths';
import { useFeedback } from '@/hooks/useFeedback';
import { isApiError } from '@/services/api';
import { listClients } from '@/services/clients';
import { createDemand } from '@/services/demands';
import type { Client, DemandCreate } from '@/types/api';

/** Quantos clientes a selecao carrega de uma vez. */
const LIMITE_DE_CLIENTES = 100;

/** Mensagem exibida quando a falha nao veio no envelope da plataforma. */
const FALHA_GENERICA = 'Nao foi possivel criar a demanda. Tente novamente.';

function mensagemDeErro(erro: unknown): string {
  return isApiError(erro) ? erro.message : FALHA_GENERICA;
}

function rotuloDoCliente(cliente: Client): string {
  return cliente.cnpj === null ? cliente.name : `${cliente.name} — ${cliente.cnpj}`;
}

export function DemandForm() {
  const navigate = useNavigate();
  const queryClient = useQueryClient();
  const { showSuccess, showError } = useFeedback();

  const idCliente = useId();
  const idTitulo = useId();
  const idContexto = useId();

  const [clientId, setClientId] = useState('');
  const [title, setTitle] = useState('');
  const [description, setDescription] = useState('');

  const clientes = useQuery({
    queryKey: ['clients', { size: LIMITE_DE_CLIENTES }],
    queryFn: ({ signal }) => listClients({ size: LIMITE_DE_CLIENTES }, { signal }),
  });

  const criacao = useMutation({
    mutationFn: (payload: DemandCreate) => createDemand(payload),
    onSuccess: async (demanda) => {
      showSuccess(`Demanda "${demanda.title}" criada.`);
      await queryClient.invalidateQueries({ queryKey: ['demands'] });
      navigate(buildPath.demandDetail(demanda.id));
    },
    onError: (erro: unknown) => showError(mensagemDeErro(erro)),
  });

  const tituloPreenchido = title.trim() !== '';
  const podeEnviar = clientId !== '' && tituloPreenchido && !criacao.isPending;

  function handleSubmit(evento: FormEvent<HTMLFormElement>) {
    evento.preventDefault();
    if (!podeEnviar) {
      return;
    }
    const contexto = description.trim();
    criacao.mutate({
      client_id: clientId,
      title: title.trim(),
      description: contexto === '' ? null : contexto,
    });
  }

  return (
    <form className="form" onSubmit={handleSubmit} aria-labelledby="titulo-nova-demanda">
      <div className="form__field">
        <label className="form__label" htmlFor={idCliente}>
          Cliente <abbr title="obrigatorio">*</abbr>
        </label>
        <select
          id={idCliente}
          className="form__control"
          value={clientId}
          required
          disabled={clientes.isPending || clientes.isError}
          onChange={(evento) => setClientId(evento.target.value)}
        >
          <option value="">
            {clientes.isPending ? 'Carregando clientes…' : 'Selecione o cliente'}
          </option>
          {(clientes.data?.items ?? []).map((cliente) => (
            <option key={cliente.id} value={cliente.id}>
              {rotuloDoCliente(cliente)}
            </option>
          ))}
        </select>
        {clientes.isError ? (
          <p className="form__hint form__hint--error" role="status">
            {mensagemDeErro(clientes.error)} Sem a lista de clientes nao e possivel abrir a
            negociacao.
          </p>
        ) : null}
        {clientes.isSuccess && clientes.data.items.length === 0 ? (
          <p className="form__hint" role="status">
            Nenhum cliente cadastrado. Cadastre o cliente antes de abrir a demanda.
          </p>
        ) : null}
      </div>

      <div className="form__field">
        <label className="form__label" htmlFor={idTitulo}>
          Titulo <abbr title="obrigatorio">*</abbr>
        </label>
        <input
          id={idTitulo}
          className="form__control"
          value={title}
          required
          maxLength={200}
          autoComplete="off"
          onChange={(evento) => setTitle(evento.target.value)}
        />
      </div>

      <div className="form__field">
        <label className="form__label" htmlFor={idContexto}>
          Contexto
        </label>
        <textarea
          id={idContexto}
          className="form__control"
          value={description}
          rows={5}
          onChange={(evento) => setDescription(evento.target.value)}
        />
        <p className="form__hint">
          O que o cliente pediu, nas palavras dele. A fonte bruta completa entra depois, na
          captacao.
        </p>
      </div>

      <div className="form__actions">
        <button className="button" type="submit" disabled={!podeEnviar}>
          {criacao.isPending ? 'Criando…' : 'Criar demanda'}
        </button>
      </div>
    </form>
  );
}
