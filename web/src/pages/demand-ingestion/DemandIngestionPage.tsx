import { useMutation, useQueryClient } from "@tanstack/react-query";
import { type FormEvent, useState } from "react";
import { Link, useNavigate, useParams } from "react-router-dom";

import { buildPath, QUERY_PARAMS } from "@/app/paths";
import { demandDetailKey } from "@/features/demands/DemandDetailQueryKeys";
import { useFeedback } from "@/hooks/useFeedback";
import { captureRawText } from "@/services/ingestion";
import { submitStructuringJob } from "@/services/structuring";
import type {
  IngestionAccepted,
  IngestionCreateRequest,
  RawInputSource,
  StructuringRequest,
} from "@/types/api";

const MAXIMO_DE_CARACTERES = 50_000;

const ORIGENS: readonly {
  readonly value: RawInputSource;
  readonly label: string;
}[] = [
  { value: "EMAIL", label: "E-mail" },
  { value: "TRANSCRICAO", label: "Transcrição de reunião" },
  { value: "MENSAGENS", label: "Mensagens" },
  { value: "ANOTACAO", label: "Anotação" },
  { value: "OUTRO", label: "Outro" },
];

export function DemandIngestionPage() {
  const { demandId } = useParams<{ demandId: string }>();
  const navigate = useNavigate();
  const queryClient = useQueryClient();
  const { showSuccess, showError } = useFeedback();
  const [text, setText] = useState("");
  const [sourceType, setSourceType] = useState<RawInputSource | "">("");
  const [validationError, setValidationError] = useState<string | null>(null);
  const [savedCapture, setSavedCapture] = useState<{
    demandId: string;
    rawInputId: string;
    text: string;
    sourceType: RawInputSource | "";
  } | null>(null);

  const generation = useMutation({
    mutationFn: (payload: StructuringRequest) => submitStructuringJob(payload),
    onSuccess: (accepted) => {
      showSuccess(
        "Curso enviado para geracao. O andamento sera atualizado nesta tela.",
      );
      navigate(
        `${buildPath.demandStructuring(accepted.demand_id)}?${QUERY_PARAMS.structuringJob}=${encodeURIComponent(accepted.job_id)}`,
      );
    },
    onError: () =>
      showError(
        "O texto foi salvo, mas nao foi possivel iniciar a geracao. Tente novamente.",
      ),
  });

  const capture = useMutation<IngestionAccepted, Error, IngestionCreateRequest>(
    {
      mutationFn: (payload) => captureRawText(payload),
      onSuccess: (response, payload) => {
        setSavedCapture({
          demandId: payload.demand_id,
          rawInputId: response.raw_input_id,
          text: payload.text,
          sourceType: payload.source_type ?? "",
        });
        void queryClient.invalidateQueries({
          queryKey: demandDetailKey(payload.demand_id),
        });
        generation.mutate({
          demand_id: payload.demand_id,
          text: payload.text,
          source_ids: [response.raw_input_id],
        });
      },
      onError: () =>
        showError("Nao foi possivel registrar o texto. Tente novamente."),
    },
  );

  const textoJaSalvo =
    savedCapture !== null &&
    savedCapture.demandId === demandId &&
    savedCapture.text === text &&
    savedCapture.sourceType === sourceType;
  const processando = capture.isPending || generation.isPending;

  function salvarTexto(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    if (demandId === undefined) {
      return;
    }

    const caracteresValidos = text.replace(/\s/g, "").length;
    if (caracteresValidos < 10) {
      setValidationError(
        "O texto precisa ter pelo menos 10 caracteres que não sejam espaços.",
      );
      return;
    }
    if (text.length > MAXIMO_DE_CARACTERES) {
      setValidationError("O texto ultrapassa o limite de 50.000 caracteres.");
      return;
    }

    setValidationError(null);
    if (textoJaSalvo && savedCapture !== null) {
      generation.mutate({
        demand_id: demandId,
        text,
        source_ids: [savedCapture.rawInputId],
      });
      return;
    }

    capture.mutate({
      demand_id: demandId,
      text,
      source_type: sourceType === "" ? null : sourceType,
    });
  }

  if (demandId === undefined) {
    return <p className="page__pending">Demanda nao informada no endereco.</p>;
  }

  return (
    <section className="page">
      <header className="page__header">
        <h1 className="page__title">Adicionar texto para o curso com IA</h1>
        <p className="page__description">
          Cole o e-mail, a transcrição ou as mensagens recebidas. O texto
          original será salvo na demanda antes de ser enviado à IA.
        </p>
        <p className="page__description">
          A geracao comeca automaticamente ao salvar. Depois, voce acompanha o
          processamento e revisa a ementa gerada.
        </p>
      </header>

      <form className="form" onSubmit={salvarTexto}>
        <label className="form__label" htmlFor="ingestion-source">
          De onde veio o texto?
        </label>
        <select
          className="form__control"
          id="ingestion-source"
          value={sourceType}
          onChange={(event) =>
            setSourceType(event.target.value as RawInputSource | "")
          }
          disabled={processando}
        >
          <option value="">Identificar automaticamente</option>
          {ORIGENS.map((origin) => (
            <option key={origin.value} value={origin.value}>
              {origin.label}
            </option>
          ))}
        </select>

        <label className="form__label" htmlFor="ingestion-text">
          Texto recebido do cliente
        </label>
        <textarea
          className="form__control"
          id="ingestion-text"
          value={text}
          onChange={(event) => {
            setText(event.target.value);
            setValidationError(null);
          }}
          placeholder="Cole aqui o pedido de treinamento recebido do cliente..."
          rows={12}
          maxLength={MAXIMO_DE_CARACTERES}
          required
          aria-invalid={validationError !== null}
          aria-describedby="ingestion-hint ingestion-validation"
          disabled={processando}
        />
        <p className="form__hint" id="ingestion-hint">
          Mínimo de 10 caracteres que não sejam espaços. O texto não será
          reescrito nesta etapa.
        </p>
        <p className="form__hint" aria-live="polite">
          {text.length.toLocaleString("pt-BR")} /{" "}
          {MAXIMO_DE_CARACTERES.toLocaleString("pt-BR")}
        </p>
        {validationError === null ? null : (
          <p
            className="form__hint form__hint--error"
            id="ingestion-validation"
            role="alert"
          >
            {validationError}
          </p>
        )}
        {generation.isError ? (
          <p className="form__hint form__hint--error" role="alert">
            O texto ja foi salvo. Clique novamente para tentar iniciar a geracao
            sem registrar outra copia.
          </p>
        ) : null}

        <div className="form__actions">
          <button className="button" type="submit" disabled={processando}>
            {capture.isPending
              ? "Salvando texto..."
              : generation.isPending
                ? "Iniciando geracao..."
                : generation.isError && textoJaSalvo
                  ? "Tentar gerar novamente"
                  : "Salvar texto e fazer o curso com IA"}
          </button>
          <Link
            className="button button--secondary"
            to={buildPath.demandDetail(demandId)}
          >
            Voltar para a demanda
          </Link>
        </div>
      </form>
    </section>
  );
}
