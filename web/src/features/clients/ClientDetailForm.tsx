/**
 * Edicao do cadastro do cliente (RF01; RF01.2 no Documento Consolidado v1.0).
 *
 * `PATCH /api/v1/clients/{client_id}` altera somente os campos enviados, e este
 * formulario envia so o que o operador mudou de fato - reenviar o cadastro
 * inteiro sobrescreveria com os mesmos valores um registro que outra pessoa
 * pode ter acabado de corrigir.
 *
 * Campo opcional esvaziado vai como `null`, nunca como `""`: o contrato declara
 * `string | null`, e string vazia gravaria "preenchido com nada", que depois
 * nao se distingue de ausencia real - a mesma regra do cadastro.
 *
 * Razao social nao pode ser limpa: o contrato aceita o campo anulavel mas exige
 * ao menos um caractere, entao a tela bloqueia o envio em vez de deixar o
 * operador descobrir a regra por um 422.
 *
 * `active` fica de fora. O schema recusa propriedade desconhecida
 * (`additionalProperties: false`) e a inativacao pertence ao RF01.3, em
 * operacao propria - enviar o campo por aqui devolveria 422.
 */

import { useMutation, useQueryClient } from '@tanstack/react-query';
import { type FormEvent, useId, useState } from 'react';

import { CLIENTS_KEY, clientDetailKey } from '@/features/clients/ClientDetailQueryKeys';
import { FieldError } from '@/components/FieldError';
import { fieldErrorsFrom, hasFieldErrors, type FieldErrors } from '@/components/fieldErrors';
import { useFeedback } from '@/hooks/useFeedback';
import { isApiError } from '@/services/api';
import { updateClient } from '@/services/clients';
import type { Client, ClientUpdate } from '@/types/api';

/** Mensagem exibida quando a falha nao veio no envelope da plataforma. */
const FALHA_GENERICA = 'Nao foi possivel salvar o cliente. Tente novamente.';

function mensagemDeErro(erro: unknown): string {
  return isApiError(erro) ? erro.message : FALHA_GENERICA;
}

/** Texto opcional vazio vira ausencia declarada (`null`), nao string vazia. */
function opcional(valor: string): string | null {
  const limpo = valor.trim();

  return limpo === '' ? null : limpo;
}

interface ClientDetailFormProps {
  /** Cliente como esta hoje; serve de valor inicial e de base da comparacao. */
  client: Client;
  /** Chamado ao salvar ou cancelar, para a tela voltar a exibicao. */
  onFinish: () => void;
}

export function ClientDetailForm({ client, onFinish }: ClientDetailFormProps) {
  const queryClient = useQueryClient();
  const { showSuccess, showError } = useFeedback();

  const idRazaoSocial = useId();
  const idCnpj = useId();
  const idSegmento = useId();
  const idContato = useId();
  const idEmail = useId();
  const idTelefone = useId();
  const idObservacoes = useId();

  const [name, setName] = useState(client.name);
  const [cnpj, setCnpj] = useState(client.cnpj ?? '');
  const [segment, setSegment] = useState(client.segment ?? '');
  const [contactName, setContactName] = useState(client.contact_name ?? '');
  const [contactEmail, setContactEmail] = useState(client.contact_email ?? '');
  const [contactPhone, setContactPhone] = useState(client.contact_phone ?? '');
  const [notes, setNotes] = useState(client.notes ?? '');
  const [errors, setErrors] = useState<FieldErrors>({});

  function clearError(field: string) {
    if (errors[field] !== undefined) {
      setErrors((current) => ({ ...current, [field]: undefined }));
    }
  }

  const edicao = useMutation({
    mutationFn: (payload: ClientUpdate) => updateClient(client.id, payload),
    onSuccess: async (atualizado) => {
      // A resposta ja e o cadastro inteiro: escrever no cache faz a tela
      // refletir a edicao sem esperar a releitura.
      queryClient.setQueryData(clientDetailKey(client.id), atualizado);
      showSuccess('Cadastro do cliente salvo.');
      onFinish();
      await queryClient.invalidateQueries({ queryKey: CLIENTS_KEY });
    },
    onError: (erro: unknown) => {
      const fieldErrors = fieldErrorsFrom(erro);
      setErrors(fieldErrors);
      if (!hasFieldErrors(fieldErrors)) showError(mensagemDeErro(erro));
    },
  });

  const razaoSocialNova = name.trim();
  const cnpjNovo = opcional(cnpj);
  const segmentoNovo = opcional(segment);
  const contatoNovo = opcional(contactName);
  const emailNovo = opcional(contactEmail);
  const telefoneNovo = opcional(contactPhone);
  const observacoesNovas = opcional(notes);

  // Cada campo entra no corpo so quando difere do que esta gravado: o que o
  // operador nao tocou nao viaja.
  const alteracoes: ClientUpdate = {
    ...(razaoSocialNova === client.name ? {} : { name: razaoSocialNova }),
    ...(cnpjNovo === client.cnpj ? {} : { cnpj: cnpjNovo }),
    ...(segmentoNovo === client.segment ? {} : { segment: segmentoNovo }),
    ...(contatoNovo === client.contact_name ? {} : { contact_name: contatoNovo }),
    ...(emailNovo === client.contact_email ? {} : { contact_email: emailNovo }),
    ...(telefoneNovo === client.contact_phone ? {} : { contact_phone: telefoneNovo }),
    ...(observacoesNovas === client.notes ? {} : { notes: observacoesNovas }),
  };

  const mudouAlgo = Object.keys(alteracoes).length > 0;
  const podeSalvar = razaoSocialNova !== '' && mudouAlgo && !edicao.isPending;

  function handleSubmit(evento: FormEvent<HTMLFormElement>) {
    evento.preventDefault();

    if (!podeSalvar) {
      return;
    }

    edicao.mutate(alteracoes);
  }

  return (
    <form className="form" onSubmit={handleSubmit} aria-label="Editar cadastro do cliente">
      <div className="form__field">
        <label className="form__label" htmlFor={idRazaoSocial}>
          Razao social <abbr title="obrigatorio">*</abbr>
        </label>
        <input
          id={idRazaoSocial}
          className="form__control"
          value={name}
          aria-invalid={errors.name !== undefined}
          aria-describedby={errors.name === undefined ? undefined : `${idRazaoSocial}-error`}
          required
          maxLength={200}
          autoComplete="off"
          onChange={(evento) => {
            setName(evento.target.value);
            clearError('name');
          }}
        />
        {razaoSocialNova === '' ? (
          <p className="form__hint form__hint--error">
            A razao social identifica a empresa e nao pode ficar vazia.
          </p>
        ) : null}
        <FieldError id={`${idRazaoSocial}-error`} message={errors.name} />
      </div>

      <div className="form__field">
        <label className="form__label" htmlFor={idCnpj}>
          CNPJ
        </label>
        <input
          id={idCnpj}
          className="form__control"
          value={cnpj}
          aria-invalid={errors.cnpj !== undefined}
          aria-describedby={errors.cnpj === undefined ? undefined : `${idCnpj}-error`}
          maxLength={18}
          autoComplete="off"
          inputMode="numeric"
          onChange={(evento) => {
            setCnpj(evento.target.value);
            clearError('cnpj');
          }}
        />
        <p className="form__hint">
          CNPJ ja usado por outra empresa e recusado pelo servico.
        </p>
        <FieldError id={`${idCnpj}-error`} message={errors.cnpj} />
      </div>

      <div className="form__field">
        <label className="form__label" htmlFor={idSegmento}>
          Segmento
        </label>
        <input
          id={idSegmento}
          className="form__control"
          value={segment}
          aria-invalid={errors.segment !== undefined}
          aria-describedby={errors.segment === undefined ? undefined : `${idSegmento}-error`}
          maxLength={120}
          autoComplete="off"
          onChange={(evento) => {
            setSegment(evento.target.value);
            clearError('segment');
          }}
        />
        <p className="form__hint">
          Ramo de atuacao da empresa. Serve de contexto para a estruturacao por IA (RF11).
        </p>
        <FieldError id={`${idSegmento}-error`} message={errors.segment} />
      </div>

      <div className="form__field">
        <label className="form__label" htmlFor={idContato}>
          Nome do contato
        </label>
        <input
          id={idContato}
          className="form__control"
          value={contactName}
          aria-invalid={errors.contact_name !== undefined}
          aria-describedby={errors.contact_name === undefined ? undefined : `${idContato}-error`}
          maxLength={200}
          autoComplete="off"
          onChange={(evento) => {
            setContactName(evento.target.value);
            clearError('contact_name');
          }}
        />
        <FieldError id={`${idContato}-error`} message={errors.contact_name} />
      </div>

      <div className="form__field">
        <label className="form__label" htmlFor={idEmail}>
          E-mail do contato
        </label>
        <input
          id={idEmail}
          className="form__control"
          type="email"
          value={contactEmail}
          aria-invalid={errors.contact_email !== undefined}
          aria-describedby={errors.contact_email === undefined ? undefined : `${idEmail}-error`}
          maxLength={200}
          autoComplete="off"
          onChange={(evento) => {
            setContactEmail(evento.target.value);
            clearError('contact_email');
          }}
        />
        <FieldError id={`${idEmail}-error`} message={errors.contact_email} />
      </div>

      <div className="form__field">
        <label className="form__label" htmlFor={idTelefone}>
          Telefone do contato
        </label>
        <input
          id={idTelefone}
          className="form__control"
          type="tel"
          value={contactPhone}
          aria-invalid={errors.contact_phone !== undefined}
          aria-describedby={errors.contact_phone === undefined ? undefined : `${idTelefone}-error`}
          maxLength={40}
          autoComplete="off"
          onChange={(evento) => {
            setContactPhone(evento.target.value);
            clearError('contact_phone');
          }}
        />
        <FieldError id={`${idTelefone}-error`} message={errors.contact_phone} />
      </div>

      <div className="form__field">
        <label className="form__label" htmlFor={idObservacoes}>
          Observacoes
        </label>
        <textarea
          id={idObservacoes}
          className="form__control"
          value={notes}
          aria-invalid={errors.notes !== undefined}
          aria-describedby={errors.notes === undefined ? undefined : `${idObservacoes}-error`}
          rows={4}
          onChange={(evento) => {
            setNotes(evento.target.value);
            clearError('notes');
          }}
        />
        <p className="form__hint">
          Historico da conta, preferencias e combinados. Apagar o campo limpa a observacao do
          cadastro.
        </p>
        <FieldError id={`${idObservacoes}-error`} message={errors.notes} />
      </div>

      <div className="form__actions">
        <button className="button" type="submit" disabled={!podeSalvar}>
          {edicao.isPending ? 'Salvando…' : 'Salvar cadastro'}
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
