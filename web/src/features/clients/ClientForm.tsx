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

  const cadastro = useMutation({
    mutationFn: (payload: ClientCreate) => createClient(payload),
    onSuccess: async (cliente) => {
      showSuccess(`Cliente "${cliente.name}" cadastrado.`);
      await queryClient.invalidateQueries({ queryKey: ['clients'] });
      navigate(PATHS.clients);
    },
    onError: (erro: unknown) => showError(mensagemDeErro(erro)),
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
          required
          maxLength={200}
          autoComplete="off"
          onChange={(evento) => setName(evento.target.value)}
        />
        <p className="form__hint">
          Unico campo obrigatorio. O restante pode ser completado depois, pela edicao do cliente.
        </p>
      </div>

      <div className="form__field">
        <label className="form__label" htmlFor={idCnpj}>
          CNPJ
        </label>
        <input
          id={idCnpj}
          className="form__control"
          value={cnpj}
          maxLength={18}
          autoComplete="off"
          inputMode="numeric"
          onChange={(evento) => setCnpj(evento.target.value)}
        />
        <p className="form__hint">
          Identificacao usada para nao cadastrar a mesma empresa duas vezes. CNPJ ja cadastrado e
          recusado pelo servico.
        </p>
      </div>

      <div className="form__field">
        <label className="form__label" htmlFor={idSegmento}>
          Segmento
        </label>
        <input
          id={idSegmento}
          className="form__control"
          value={segment}
          maxLength={120}
          autoComplete="off"
          onChange={(evento) => setSegment(evento.target.value)}
        />
        <p className="form__hint">
          Ramo de atuacao da empresa. Serve de contexto para a estruturacao por IA (RF11).
        </p>
      </div>

      <div className="form__field">
        <label className="form__label" htmlFor={idContato}>
          Nome do contato
        </label>
        <input
          id={idContato}
          className="form__control"
          value={contactName}
          maxLength={200}
          autoComplete="off"
          onChange={(evento) => setContactName(evento.target.value)}
        />
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
          maxLength={200}
          autoComplete="off"
          onChange={(evento) => setContactEmail(evento.target.value)}
        />
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
          maxLength={40}
          autoComplete="off"
          onChange={(evento) => setContactPhone(evento.target.value)}
        />
      </div>

      <div className="form__field">
        <label className="form__label" htmlFor={idObservacoes}>
          Observacoes
        </label>
        <textarea
          id={idObservacoes}
          className="form__control"
          value={notes}
          rows={4}
          onChange={(evento) => setNotes(evento.target.value)}
        />
        <p className="form__hint">
          Historico da conta, preferencias e combinados. O que o cliente pediu vai na demanda, nao
          aqui.
        </p>
      </div>

      <div className="form__actions">
        <button className="button" type="submit" disabled={!podeEnviar}>
          {cadastro.isPending ? 'Cadastrando…' : 'Cadastrar cliente'}
        </button>
      </div>
    </form>
  );
}
