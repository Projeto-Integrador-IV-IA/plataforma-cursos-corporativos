/**
 * Formulario de cadastro de cliente (RF01; RF01.1 no Documento Consolidado
 * v1.0).
 *
 * Primeira tela de escrita do sistema: sem cliente cadastrado nao ha demanda a
 * abrir (RF02), entao esta e a porta de entrada da demonstracao.
 *
 * So `name` e obrigatorio no contrato (`ClientCreate`), e o formulario respeita
 * isso - o operador costuma receber a razao social antes do resto, e travar o
 * cadastro por falta de CNPJ empurraria o dado para fora do sistema. Os demais
 * campos sao completados depois, pela edicao do cliente (RF01.2).
 *
 * Campo opcional deixado em branco vai como `null`, nunca como `""`: o contrato
 * declara `string | null` e string vazia gravaria "preenchido com nada", que
 * depois nao se distingue de ausencia real.
 *
 * `active` nao aparece aqui: o cliente nasce ativo pelo servico e a inativacao
 * e operacao propria (RF01.3), fora deste card.
 */

import { useMutation, useQueryClient } from '@tanstack/react-query';
import { type FormEvent, useId, useState } from 'react';
import { useNavigate } from 'react-router-dom';

import { PATHS } from '@/app/paths';
import { FieldError } from '@/components/FieldError';
import { fieldErrorsFrom, hasFieldErrors, type FieldErrors } from '@/components/fieldErrors';
import { useFeedback } from '@/hooks/useFeedback';
import { isApiError } from '@/services/api';
import { createClient } from '@/services/clients';
import type { ClientCreate } from '@/types/api';

/** Mensagem exibida quando a falha nao veio no envelope da plataforma. */
const FALHA_GENERICA = 'Nao foi possivel cadastrar o cliente. Tente novamente.';

function mensagemDeErro(erro: unknown): string {
  return isApiError(erro) ? erro.message : FALHA_GENERICA;
}

/** Texto opcional vazio vira ausencia declarada (`null`), nao string vazia. */
function opcional(valor: string): string | null {
  const limpo = valor.trim();

  return limpo === '' ? null : limpo;
}

export function ClientForm() {
  const navigate = useNavigate();
  const queryClient = useQueryClient();
  const { showSuccess, showError } = useFeedback();

  const idRazaoSocial = useId();
  const idCnpj = useId();
  const idSegmento = useId();
  const idContato = useId();
  const idEmail = useId();
  const idTelefone = useId();
  const idObservacoes = useId();

  const [name, setName] = useState('');
  const [cnpj, setCnpj] = useState('');
  const [segment, setSegment] = useState('');
  const [contactName, setContactName] = useState('');
  const [contactEmail, setContactEmail] = useState('');
  const [contactPhone, setContactPhone] = useState('');
  const [notes, setNotes] = useState('');
  const [errors, setErrors] = useState<FieldErrors>({});

  function clearError(field: string) {
    if (errors[field] !== undefined) {
      setErrors((current) => ({ ...current, [field]: undefined }));
    }
  }

  const cadastro = useMutation({
    mutationFn: (payload: ClientCreate) => createClient(payload),
    onSuccess: async (cliente) => {
      showSuccess(`Cliente "${cliente.name}" cadastrado.`);
      await queryClient.invalidateQueries({ queryKey: ['clients'] });
      navigate(PATHS.clients);
    },
    onError: (erro: unknown) => {
      const fieldErrors = fieldErrorsFrom(erro);
      setErrors(fieldErrors);
      if (!hasFieldErrors(fieldErrors)) showError(mensagemDeErro(erro));
    },
  });

  const podeEnviar = name.trim() !== '' && !cadastro.isPending;

  function handleSubmit(evento: FormEvent<HTMLFormElement>) {
    evento.preventDefault();
    if (!podeEnviar) {
      return;
    }
    cadastro.mutate({
      name: name.trim(),
      cnpj: opcional(cnpj),
      segment: opcional(segment),
      contact_name: opcional(contactName),
      contact_email: opcional(contactEmail),
      contact_phone: opcional(contactPhone),
      notes: opcional(notes),
    });
  }

  return (
    <form className="form" onSubmit={handleSubmit} aria-labelledby="titulo-novo-cliente">
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
        <p className="form__hint">
          Unico campo obrigatorio. O restante pode ser completado depois, pela edicao do cliente.
        </p>
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
          Identificacao usada para nao cadastrar a mesma empresa duas vezes. CNPJ ja cadastrado e
          recusado pelo servico.
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
          Historico da conta, preferencias e combinados. O que o cliente pediu vai na demanda, nao
          aqui.
        </p>
        <FieldError id={`${idObservacoes}-error`} message={errors.notes} />
      </div>

      <div className="form__actions">
        <button className="button" type="submit" disabled={!podeEnviar}>
          {cadastro.isPending ? 'Cadastrando…' : 'Cadastrar cliente'}
        </button>
      </div>
    </form>
  );
}
