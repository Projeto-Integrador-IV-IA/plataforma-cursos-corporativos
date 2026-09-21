/**
 * Tipos derivados dos contratos de API (RNF02).
 *
 * Fonte da verdade: `packages/contracts/openapi/*.yaml` e
 * `packages/contracts/schemas/*.json`. Estes tipos acompanham o contrato -
 * quando ele muda, mudam aqui, no mesmo PR.
 *
 * Duas procedencias convivem neste arquivo, e cada bloco diz qual e a sua:
 *  - DERIVADO: o contrato ja declara a operacao e o schema; o tipo espelha o
 *    contrato campo a campo e divergencia quebra a compilacao;
 *  - PREVISTO: o contrato do servico ainda e esqueleto. O tipo segue o
 *    dicionario de dados (docs/03-dados/dicionario-de-dados.md) e as convencoes
 *    de docs/02-arquitetura/contratos-api.md, e sera CONFIRMADO quando o
 *    contrato for publicado.
 */

// ---------------------------------------------------------------------------
// Convencoes gerais (docs/02-arquitetura/contratos-api.md)
// ---------------------------------------------------------------------------

/** Identificador de recurso: UUID em toda a plataforma. */
export type Uuid = string;

/** Data e hora ISO 8601 com fuso. Ex.: `2026-09-15T14:30:00-03:00`. */
export type IsoDateTime = string;

/** Valor JSON arbitrario. Existe para nunca precisarmos de `any`. */
export type JsonValue = string | number | boolean | null | readonly JsonValue[] | JsonObject;

/**
 * Objeto JSON arbitrario, como `content` e `ai_metadata` de uma versao.
 * Chave ausente e `undefined` porque campo opcional simplesmente nao e
 * serializado.
 */
export type JsonObject = { readonly [key: string]: JsonValue | undefined };

/**
 * Envelope de listagem paginada: `?page=1&size=20` na entrada, `items`,
 * `total`, `page` e `size` na saida.
 */
export interface Page<TItem> {
  readonly items: readonly TItem[];
  readonly total: number;
  readonly page: number;
  readonly size: number;
}

/** Parametros de paginacao aceitos por toda listagem. */
export interface PageParams {
  readonly page?: number;
  readonly size?: number;
}

// ---------------------------------------------------------------------------
// Erro - DERIVADO de packages/contracts/schemas/error.schema.json
// (e de `DemandErrorResponse` em pipeline-service.yaml, que e o mesmo envelope)
// ---------------------------------------------------------------------------

/**
 * Corpo do erro. `code` e estavel e legivel por maquina; `message` e em
 * portugues e exibivel ao operador (RNF10); `request_id` correlaciona a
 * requisicao no log (RNF09).
 *
 * `details` e aberto no schema da plataforma; o pipeline-service hoje so emite
 * valores string. Tipar como `JsonValue` aceita os dois sem mentir sobre o
 * contrato.
 */
export interface ApiErrorDetails {
  readonly code: string;
  readonly message: string;
  readonly details?: Readonly<Record<string, JsonValue>>;
  readonly request_id?: string | null;
}

/** Envelope de erro unico da plataforma: `{ "error": { ... } }`. */
export interface ApiErrorResponse {
  readonly error: ApiErrorDetails;
}

// ---------------------------------------------------------------------------
// Demandas - DERIVADO de packages/contracts/openapi/pipeline-service.yaml
// ---------------------------------------------------------------------------

/** Etapas percorridas por uma demanda no pipeline (RF05). */
export const PIPELINE_STAGES = [
  'CAPTACAO',
  'ESTRUTURACAO',
  'PRODUTO',
  'PROPOSTA',
  'ACOMPANHAMENTO',
] as const;

export type PipelineStage = (typeof PIPELINE_STAGES)[number];

/** Situacoes da demanda, ortogonais a etapa corrente. */
export const DEMAND_STATUSES = ['ABERTA', 'GANHA', 'PERDIDA', 'CANCELADA'] as const;

export type DemandStatus = (typeof DEMAND_STATUSES)[number];

/**
 * Corpo de `POST /api/v1/demands`. Situacao e etapa inicial sao definidas pelo
 * servico, nunca enviadas pelo cliente.
 */
export interface DemandCreate {
  readonly client_id: Uuid;
  readonly title: string;
  readonly description?: string | null;
  readonly owner_id?: Uuid | null;
}

/** Demanda persistida, com situacao, etapa corrente e vinculo ao cliente. */
export interface DemandRead {
  readonly id: Uuid;
  readonly client_id: Uuid;
  readonly title: string;
  readonly description: string | null;
  readonly owner_id: Uuid | null;
  readonly status: DemandStatus;
  readonly current_stage: PipelineStage;
  readonly active: boolean;
  readonly created_at: IsoDateTime;
  readonly updated_at: IsoDateTime;
}

/**
 * PREVISTO. Edicao de demanda (RF02): campos opcionais sobre os mesmos nomes
 * de `DemandCreate`. Etapa e situacao nao entram aqui - mudam por operacao
 * propria do pipeline (RF05, RF06).
 */
export type DemandUpdate = Partial<Omit<DemandCreate, 'client_id'>>;

/** PREVISTO. Filtros de listagem de demandas (RF03). */
export interface OffsetParams {
  readonly limit?: number;
  readonly offset?: number;
}

/**
 * Filtros de `GET /api/v1/demands`, combinados com AND.
 *
 * A entrada pagina por `limit`/`offset`; a saida volta em `page`/`size`, no
 * envelope `Page`. Os dois formatos convivem de proposito no contrato do
 * servico, e nao e engano deste arquivo.
 */
export interface DemandListParams extends OffsetParams {
  readonly status?: DemandStatus;
  readonly client_id?: Uuid;
  readonly stage?: PipelineStage;
  readonly owner_id?: Uuid;
  readonly from?: IsoDateTime;
  readonly to?: IsoDateTime;
}

// ---------------------------------------------------------------------------
// Clientes - PREVISTO (RF01), conforme `clients` no dicionario de dados
// ---------------------------------------------------------------------------

/** Empresa cliente. `segment` e insumo da estruturacao por IA (RF11). */
export interface Client {
  readonly id: Uuid;
  readonly name: string;
  readonly cnpj: string | null;
  readonly segment: string | null;
  readonly contact_name: string | null;
  readonly contact_email: string | null;
  readonly contact_phone: string | null;
  readonly notes: string | null;
  readonly active: boolean;
  readonly created_at: IsoDateTime;
  readonly updated_at: IsoDateTime;
}

/** Cadastro de cliente: so `name` e obrigatorio. */
export interface ClientCreate {
  readonly name: string;
  readonly cnpj?: string | null;
  readonly segment?: string | null;
  readonly contact_name?: string | null;
  readonly contact_email?: string | null;
  readonly contact_phone?: string | null;
  readonly notes?: string | null;
}

/** Edicao de cliente. Desativacao e logica, por `active`. */
export type ClientUpdate = Partial<ClientCreate> & { readonly active?: boolean };

/** Filtros de listagem de clientes (RF03). */
export interface ClientListParams extends PageParams {
  readonly search?: string;
  readonly active?: boolean;
}

// ---------------------------------------------------------------------------
// Ingestao - PREVISTO (RF09, RF10), conforme `raw_inputs` no dicionario
// ---------------------------------------------------------------------------

/** Procedencia do texto bruto registrado pelo operador. */
export const RAW_INPUT_SOURCES = [
  'EMAIL',
  'TRANSCRICAO',
  'MENSAGENS',
  'ANOTACAO',
  'OUTRO',
] as const;

export type RawInputSource = (typeof RAW_INPUT_SOURCES)[number];

/**
 * Demanda bruta. `original_content` e o texto exatamente como chegou e nunca e
 * alterado - e a garantia de RNF05. `normalized_content` e nulo enquanto a
 * normalizacao (RF10) nao roda.
 */
export interface RawInput {
  readonly id: Uuid;
  readonly demand_id: Uuid;
  readonly original_content: string;
  readonly normalized_content: string | null;
  readonly source: RawInputSource;
  readonly truncated: boolean;
  readonly author_id: Uuid;
  readonly created_at: IsoDateTime;
}

/** Registro de demanda bruta. O autor vem do token, nunca do corpo. */
export interface RawInputCreate {
  readonly original_content: string;
  readonly source: RawInputSource;
}

// ---------------------------------------------------------------------------
// Pipeline - PREVISTO (RF05, RF06, RF07), conforme `stage_transitions`
// ---------------------------------------------------------------------------

/** Transicao de etapa registrada. Historico append-only (RNF09). */
export interface StageTransition {
  readonly id: Uuid;
  readonly demand_id: Uuid;
  readonly from_stage: PipelineStage | null;
  readonly to_stage: PipelineStage;
  readonly reason: string | null;
  readonly author_id: Uuid;
  readonly occurred_at: IsoDateTime;
}

/**
 * Pedido de transicao. `reason` e obrigatorio no retrocesso (RF06) - regra de
 * negocio validada pelo servico, por isso o tipo o mantem opcional.
 */
export interface StageTransitionCreate {
  readonly to_stage: PipelineStage;
  readonly reason?: string | null;
}

// ---------------------------------------------------------------------------
// Artefatos - PREVISTO (RF08, RF15), conforme `artifacts`/`artifact_versions`
// ---------------------------------------------------------------------------

export const ARTIFACT_TYPES = [
  'DEMANDA_BRUTA',
  'REQUISITOS_EXTRAIDOS',
  'EMENTA',
  'PROPOSTA',
  'OUTRO',
] as const;

export type ArtifactType = (typeof ARTIFACT_TYPES)[number];

/** Origem de uma versao: distingue o gerado pela IA do revisado (RF14). */
export const ARTIFACT_VERSION_ORIGINS = ['IA', 'HUMANO'] as const;

export type ArtifactVersionOrigin = (typeof ARTIFACT_VERSION_ORIGINS)[number];

/** Documento da negociacao. Todo artefato pertence a uma demanda. */
export interface Artifact {
  readonly id: Uuid;
  readonly demand_id: Uuid;
  readonly type: ArtifactType;
  readonly title: string | null;
  readonly raw_input_id: Uuid | null;
  readonly created_at: IsoDateTime;
}

/** Metadados de uma versao gerada pela IA (RNF04). */
export type ArtifactAiMetadata = {
  readonly modelo?: string;
  readonly versao_prompt?: string;
  readonly tokens_entrada?: number;
  readonly tokens_saida?: number;
  readonly latencia_ms?: number;
  readonly tentativas?: number;
};

/**
 * Versao de artefato. Append-only (RF08, RNF09): editar cria linha nova e a
 * anterior permanece recuperavel. `author_id` so e nulo quando `origin` e `IA`.
 */
export interface ArtifactVersion {
  readonly id: Uuid;
  readonly artifact_id: Uuid;
  readonly number: number;
  readonly content: JsonObject;
  readonly origin: ArtifactVersionOrigin;
  readonly ai_metadata: ArtifactAiMetadata | null;
  readonly author_id: Uuid | null;
  readonly created_at: IsoDateTime;
}

/** Nova versao criada por revisao humana (RF14). */
export interface ArtifactVersionCreate {
  readonly content: JsonObject;
}

/**
 * Tipo de lacuna apontada pela estruturacao para um campo (RNF03).
 *
 * Cada tipo pede uma conversa diferente com o cliente: o que esta `ausente` se
 * pergunta, o que esta `ambigua` se esclarece e o que esta `contraditoria` se
 * confronta. E por isso que a tela de revisao (RF14) destaca o tipo, nao so o
 * nome do campo.
 */
export const GAP_KINDS = ['ausente', 'ambigua', 'contraditoria'] as const;

export type GapKind = (typeof GAP_KINDS)[number];

/**
 * PREVISTO. Apontamento de um campo que ficou sem valor utilizavel. `motivo` e
 * nulo quando o modelo nao registrou explicacao - a lacuna continua visivel na
 * revisao, so sem o porque.
 */
export interface FieldGap {
  readonly campo: string;
  readonly tipo: GapKind;
  readonly motivo: string | null;
}

/**
 * PREVISTO. Saida canonica da estruturacao por IA (RF11, RF12).
 * `structured-course.schema.json` ainda e esqueleto: os campos abaixo sao os
 * previstos na PoC e serao confirmados quando o schema for publicado. Por isso
 * o conteudo e tratado como JSON validado pelo servico (RNF03), e a interface
 * so depende do que ja esta acordado.
 */
export type StructuredCourse = {
  readonly tema?: string;
  readonly nicho?: string;
  readonly publico_alvo?: string;
  readonly numero_participantes?: number;
  readonly carga_horaria?: number;
  readonly formato?: string;
  readonly objetivos_aprendizagem?: readonly string[];
  readonly ementa?: readonly string[];
  /**
   * Campo sem valor utilizavel no texto de entrada e apontado aqui, nunca
   * inferido (RF14). Cada item traz o campo, o tipo da lacuna e o motivo.
   */
  readonly campos_ausentes?: readonly FieldGap[];
  readonly observacoes?: readonly string[];
};

/** Pedido de estruturacao de uma demanda bruta pela IA (RF11). */
export interface StructuringRequest {
  readonly raw_input_id: Uuid;
}
