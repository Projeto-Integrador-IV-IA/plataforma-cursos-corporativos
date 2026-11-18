/**
 * Decisao da revisao: aprovar, rejeitar ou devolver a estrutura (RF19.2, card #102).
 *
 * E o desfecho que faltava depois de ler a estrutura inteira (RF14): sem
 * isto, a IA gera e ninguem registra formalmente que uma pessoa conferiu -
 * so havia edicao (RF19.1), nunca uma decisao. `version_number` enviado e
 * sempre a versao vigente no instante do clique; se alguem editou entre a
 * tela abrir e a decisao, o servico recusa com 409 e esta tela pede para
 * recarregar em vez de repetir silenciosamente contra a versao antiga.
 */

import { useMutation, useQueryClient } from '@tanstack/react-query';
import { useState } from 'react';

import { PermissionGate } from '@/features/auth/Authorization';
import { PERMISSIONS } from '@/features/auth/permissions';
import { formatarDataHora } from '@/features/demands/DemandDetailLabels';
import { demandArtifactsKey } from '@/features/demands/DemandStructuringQueryKeys';
import { useFeedback } from '@/hooks/useFeedback';
import { isApiError } from '@/services/api';
import { reviewArtifact } from '@/services/artifacts';
import type { ArtifactReviewDecision, ArtifactReviewRead, Uuid } from '@/types/api';

const FALHA_GENERICA = 'Nao foi possivel registrar a decisao. Tente novamente.';
const FALHA_VERSAO_DESATUALIZADA =
  'A estrutura foi alterada depois que esta tela carregou. Recarregue a pagina antes de decidir.';

const ROTULO_DA_DECISAO: Record<ArtifactReviewDecision, string> = {
  APROVADO: 'Aprovada',
  REJEITADO: 'Rejeitada',
  DEVOLVIDO: 'Devolvida',
};

function mensagemDeErro(error: unknown): string {
  if (isApiError(error)) {
    return error.code === 'ARTIFACT_VERSION_STALE' ? FALHA_VERSAO_DESATUALIZADA : error.message;
  }

  return FALHA_GENERICA;
}

interface DemandStructuringReviewProps {
  demandId: Uuid;
  artifactId: Uuid;
  versionNumber: number;
  latestReview: ArtifactReviewRead | null;
}

export function DemandStructuringReview({
  demandId,
  artifactId,
  versionNumber,
  latestReview,
}: DemandStructuringReviewProps) {
  const queryClient = useQueryClient();
  const { showSuccess, showError } = useFeedback();
  const [reason, setReason] = useState('');
  const [reasonError, setReasonError] = useState<string | null>(null);

  const review = useMutation({
    mutationFn: (decision: ArtifactReviewDecision) =>
      reviewArtifact(artifactId, {
        version_number: versionNumber,
        decision,
        reason: reason.trim() === '' ? null : reason.trim(),
      }),
    onSuccess: (registrada) => {
      setReason('');
      setReasonError(null);
      showSuccess(`Decisao registrada: ${ROTULO_DA_DECISAO[registrada.decision].toLowerCase()}.`);
      void queryClient.invalidateQueries({ queryKey: demandArtifactsKey(demandId) });
    },
    onError: (error: unknown) => showError(mensagemDeErro(error)),
  });

  function decidir(decision: ArtifactReviewDecision): void {
    if (decision !== 'APROVADO' && reason.trim() === '') {
      setReasonError('Justificativa obrigatoria para rejeitar ou devolver.');
      return;
    }

    setReasonError(null);
    review.mutate(decision);
  }

  const revisadaNestaVersao = latestReview !== null && latestReview.version_number === versionNumber;

  return (
    <PermissionGate permission={PERMISSIONS.structuringReview}>
      <div className="structuring-review">
        {revisadaNestaVersao ? (
          <p className="structuring-review__current" role="status">
            Ultima decisao: <strong>{ROTULO_DA_DECISAO[latestReview.decision]}</strong> em{' '}
            {formatarDataHora(latestReview.created_at)}
            {latestReview.reason === null ? null : ` — "${latestReview.reason}"`}
          </p>
        ) : null}

        <label className="form__label" htmlFor="revisao-justificativa">
          Justificativa (obrigatoria para rejeitar ou devolver)
        </label>
        <textarea
          id="revisao-justificativa"
          className="form__control"
          rows={3}
          value={reason}
          disabled={review.isPending}
          onChange={(event) => {
            setReason(event.target.value);
            setReasonError(null);
          }}
          aria-describedby={reasonError === null ? undefined : 'revisao-justificativa-erro'}
        />
        {reasonError === null ? null : (
          <p className="form__hint form__hint--error" id="revisao-justificativa-erro" role="alert">
            {reasonError}
          </p>
        )}

        <div className="form__actions">
          <button
            type="button"
            className="button"
            disabled={review.isPending}
            onClick={() => decidir('APROVADO')}
          >
            {review.isPending && review.variables === 'APROVADO' ? 'Aprovando…' : 'Aprovar'}
          </button>
          <button
            type="button"
            className="button button--secondary"
            disabled={review.isPending}
            onClick={() => decidir('DEVOLVIDO')}
          >
            {review.isPending && review.variables === 'DEVOLVIDO' ? 'Devolvendo…' : 'Devolver'}
          </button>
          <button
            type="button"
            className="button button--danger"
            disabled={review.isPending}
            onClick={() => decidir('REJEITADO')}
          >
            {review.isPending && review.variables === 'REJEITADO' ? 'Rejeitando…' : 'Rejeitar'}
          </button>
        </div>
      </div>
    </PermissionGate>
  );
}
