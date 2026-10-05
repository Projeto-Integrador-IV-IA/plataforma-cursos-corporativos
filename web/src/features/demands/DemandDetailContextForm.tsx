/**
 * Edicao do contexto da demanda (RF02).
 *
 * `PATCH /api/v1/demands/{id}` altera somente os campos enviados, e este
 * formulario envia so o que o operador mudou de fato - um contexto reenviado
 * igual viraria uma escrita sem motivo no historico da negociacao.
 *
 * Titulo nao pode ser limpo: o contrato o aceita anulavel mas exige ao menos
 * um caractere, entao a tela bloqueia o envio em vez de deixar o operador
 * descobrir a regra por um 422.
 *
 * Etapa e situacao ficam de fora: quem as move e o pipeline (RF05, RF06), que
 * registra a transicao. Responsavel tambem fica: a API aceita `owner_id`, mas
 * ainda nao ha endpoint que liste usuarios de onde escolher - a mesma razao
 * pela qual o formulario de abertura nao o oferece.
 */

import { useMutation, useQueryClient } from '@tanstack/react-query';
import { type FormEvent, useId, useState } from 'react';

import { DEMANDS_KEY, demandDetailKey } from '@/features/demands/DemandDetailQueryKeys';
import { useFeedback } from '@/hooks/useFeedback';
import { isApiError } from '@/services/api';
import { updateDemand } from '@/services/demands';
import type { DemandDetail, DemandUpdate } from '@/types/api';

/** Mensagem exibida quando a falha nao veio no envelope da plataforma. */
const FALHA_GENERICA = 'Nao foi possivel salvar o contexto. Tente novamente.';

function mensagemDeErro(erro: unknown): string {
  return isApiError(erro) ? erro.message : FALHA_GENERICA;
}

interface DemandDetailContextFormProps {
  /** Demanda como esta hoje; serve de valor inicial e de base da comparacao. */
  demand: DemandDetail;
  /** Chamado ao salvar ou cancelar, para a tela voltar a exibicao. */
  onFinish: () => void;
}

export function DemandDetailContextForm({ demand, onFinish }: DemandDetailContextFormProps) {
  const queryClient = useQueryClient();
  const { showSuccess, showError } = useFeedback();

  const idTitulo = useId();
  const idContexto = useId();

  const [title, setTitle] = useState(demand.title);
  const [description, setDescription] = useState(demand.description ?? '');

  const edicao = useMutation({
    mutationFn: (payload: DemandUpdate) => updateDemand(demand.id, payload),
    onSuccess: async (atualizada) => {
      // A resposta ja e o agregado inteiro: escrever no cache faz a tela
      // refletir a edicao sem esperar a releitura.
      queryClient.setQueryData(demandDetailKey(demand.id), atualizada);
      showSuccess('Contexto da demanda salvo.');
      onFinish();
      await queryClient.invalidateQueries({ queryKey: DEMANDS_KEY });
    },
    onError: (erro: unknown) => showError(mensagemDeErro(erro)),
  });

  const tituloNovo = title.trim();
  const contextoDigitado = description.trim();
  const contextoNovo = contextoDigitado === '' ? null : contextoDigitado;

  const mudouTitulo = tituloNovo !== demand.title;
  const mudouContexto = contextoNovo !== demand.description;

  const podeSalvar = tituloNovo !== '' && (mudouTitulo || mudouContexto) && !edicao.isPending;

  function handleSubmit(evento: FormEvent<HTMLFormElement>) {
    evento.preventDefault();

    if (!podeSalvar) {
      return;
    }

    edicao.mutate({
      ...(mudouTitulo ? { title: tituloNovo } : {}),
      ...(mudouContexto ? { description: contextoNovo } : {}),
    });
  }

  return (
    <form className="form" onSubmit={handleSubmit} aria-label="Editar contexto da demanda">
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
        {tituloNovo === '' ? (
          <p className="form__hint form__hint--error">
            O titulo identifica a negociacao e nao pode ficar vazio.
          </p>
        ) : null}
      </div>

      <div className="form__field">
        <label className="form__label" htmlFor={idContexto}>
          Contexto
        </label>
        <textarea
          id={idContexto}
          className="form__control"
          value={description}
          rows={6}
          onChange={(evento) => setDescription(evento.target.value)}
        />
        <p className="form__hint">
          O que o cliente pediu, nas palavras dele. Apagar o campo limpa o contexto da demanda.
        </p>
      </div>

      <div className="form__actions">
        <button className="button" type="submit" disabled={!podeSalvar}>
          {edicao.isPending ? 'Salvando…' : 'Salvar contexto'}
        </button>
        <button
          className="button button--secondary"
          type="button"
          disabled={edicao.isPending}
          onClick={onFinish}
        >
          Cancelar
        </button>
      </div>
    </form>
  );
}
