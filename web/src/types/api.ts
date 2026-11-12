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

// ---------------------------------------------------------------------------
// Autenticacao - DERIVADO de packages/contracts/openapi/gateway-service.yaml
// (`LoginRequest`, `OperatorInfo`, `TokenResponse` e `SessionResponse`)
// ---------------------------------------------------------------------------

/** Credenciais aceitas por `POST /api/v1/auth/login`. */
export interface LoginCredentials {
  readonly email: string;
  readonly password: string;
}

/** Operador autenticado, presente nas respostas de login e verificacao. */
export interface OperatorInfo {
  readonly id: Uuid;
  readonly name: string;
  readonly email: string;
  readonly role: string;
}

/** Token emitido pelo gateway apos credenciais validas. */
export interface TokenResponse {
  readonly access_token: string;
  readonly token_type?: string;
  readonly expires_in: number;
  readonly operator: OperatorInfo;
}

/** Resultado de `GET /api/v1/auth/verify`. */
export interface SessionResponse {
  readonly active?: boolean;
  readonly operator: OperatorInfo;
}

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
 * Corpo de `PATCH /api/v1/demands/{demand_id}`: campos opcionais sobre os
 * mesmos nomes de `DemandCreate`. Etapa e situacao nao entram aqui - mudam por
 * operacao propria do pipeline (RF05, RF06).
 *
 * `title` fica `string` e nao `string | null`: o contrato declara o campo
 * anulavel, mas com `minLength: 1`, entao `null` e recusado com 422. Tipar o
 * que o servico aceita evita oferecer ao operador um caminho que sempre falha.
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
// Detalhe da demanda - DERIVADO de packages/contracts/openapi/pipeline-service.yaml
// (`DemandDetail` e seus agregados: resposta de GET e de PATCH
//  /api/v1/demands/{demand_id})
// ---------------------------------------------------------------------------

/**
 * Cliente embutido no detalhe, para a tela nao precisar de uma segunda
 * consulta.
 *
 * E um recorte de `Client`, nao o mesmo tipo: o agregado nao devolve
 * `created_at` nem `updated_at` do cliente. Reaproveitar `Client` faria a tela
 * prometer campos que a resposta nao traz.
 */
export interface DemandClientRead {
  readonly id: Uuid;
  readonly name: string;
  readonly cnpj: string | null;
  readonly segment: string | null;
  readonly contact_name: string | null;
  readonly contact_email: string | null;
  readonly contact_phone: string | null;
  readonly notes: string | null;
  readonly active: boolean;
}

/**
 * Fonte captada como o detalhe a entrega (RF09, RNF05).
 *
 * O texto original vem por inteiro, e nao resumido: preserva-lo e o proprio
 * requisito, e e por ele que a revisao da estruturacao (RF19) mostra de onde
 * cada campo gerado saiu. `normalized_content` nao entra - o contrato nao o
 * declara neste agregado.
 */
export interface DemandRawInputRead {
  readonly id: Uuid;
  readonly source: RawInputSource;
  readonly original_content: string;
  readonly truncated: boolean;
  readonly author_id: Uuid;
  readonly created_at: IsoDateTime;
}

/**
 * Versao de artefato como o detalhe a entrega.
 *
 * `origin` e `ai_metadata` ficam abertos (`string` e objeto JSON) porque e
 * assim que o contrato os declara neste agregado - e nao como
 * `ArtifactVersionOrigin` e `ArtifactAiMetadata`. Estreitar aqui afirmaria uma
 * garantia que a resposta nao da; quem exibe trata o valor desconhecido.
 */
export interface DemandArtifactVersionRead {
  readonly id: Uuid;
  readonly number: number;
  readonly content: JsonObject;
  readonly origin: string;
  readonly ai_metadata: JsonObject | null;
  readonly author_id: Uuid | null;
  readonly created_at: IsoDateTime;
}

/** Artefato vinculado a demanda, com suas versoes em ordem crescente. */
export interface DemandArtifactRead {
  readonly id: Uuid;
  readonly type: string;
  readonly title: string | null;
  readonly raw_input_id: Uuid | null;
  readonly created_at: IsoDateTime;
  readonly versions: readonly DemandArtifactVersionRead[];
}

/**
 * Agregado da tela de detalhe: os campos de `DemandRead` mais o cliente e os
 * artefatos. E o que `GET` e `PATCH /api/v1/demands/{demand_id}` devolvem -
 * nao `DemandRead`, como este arquivo supunha enquanto a operacao nao estava
 * publicada.
 *
 * As fontes captadas entram em `raw_inputs`: o contrato as declara no agregado
 * (`DemandRawInputRead`), e e de la que a revisao da estruturacao (RF19) tira
 * o texto que originou cada campo gerado.
 */
export interface DemandDetail extends DemandRead {
  readonly client: DemandClientRead;
  readonly raw_inputs: readonly DemandRawInputRead[];
  readonly artifacts: readonly DemandArtifactRead[];
}

// ---------------------------------------------------------------------------
// Clientes - DERIVADO de packages/contracts/openapi/pipeline-service.yaml
// ---------------------------------------------------------------------------

/**
 * Empresa cliente, espelho de `ClientRead`. `segment` e insumo da estruturacao
 * por IA (RF11).
 */
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

/** Corpo de `POST /api/v1/clients`: so `name` e obrigatorio. */
export interface ClientCreate {
  readonly name: string;
  readonly cnpj?: string | null;
  readonly segment?: string | null;
  readonly contact_name?: string | null;
  readonly contact_email?: string | null;
  readonly contact_phone?: string | null;
  readonly notes?: string | null;
}

/**
 * Corpo de `PATCH /api/v1/clients/{id}`: campos omitidos permanecem
 * inalterados, e campo opcional enviado como `null` e limpo.
 *
 * `active` NAO entra aqui. O schema do contrato recusa propriedade
 * desconhecida (`additionalProperties: false`) e declara que a inativacao
 * pertence ao RF01.3, em operacao propria - enviar `active` nesta chamada
 * devolveria 422.
 */
export type ClientUpdate = Partial<ClientCreate>;

/**
 * Parametros de listagem de clientes (RF03).
 *
 * DERIVADO: `GET /api/v1/clients` declara somente `page` e `size`, e o tipo
 * para aqui. Ate a tela de listagem existir, este tipo previa tambem `search` e
 * `active`; a tela chegou e a previsao nao se confirmou. Mante-los custaria
 * mais do que a busca que prometem: o servico descarta parametro desconhecido,
 * entao `listClients({ search })` devolveria a base inteira paginada, e a tela
 * mostraria a primeira pagina como se fosse o resultado da busca. Filtrar as 20
 * linhas ja recebidas seria a mesma mentira, so que mais convincente.
 *
 * Busca por nome e recorte por situacao sao desejaveis nesta tela. Entram aqui
 * depois de entrarem em `packages/contracts/openapi/pipeline-service.yaml` e no
 * servico (RNF02) - contrato antes de codigo, nao o contrario.
 */
export type ClientListParams = PageParams;

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
// Visao de pipeline - DERIVADO de packages/contracts/openapi/pipeline-service.yaml
// (`PipelineBoard` e seus agregados: resposta de GET /api/v1/pipeline)
// ---------------------------------------------------------------------------

/**
 * Cliente ou responsavel como o cartao os recebe: nome e identificador, nada
 * mais.
 *
 * Nao e `Client` nem um recorte dele: o quadro reduz de proposito a pessoa ao
 * que a coluna desenha. Reaproveitar `Client` aqui faria o cartao prometer
 * CNPJ, segmento e contato que a resposta do quadro nao traz.
 */
export interface PipelineCardPersonRead {
  readonly id: Uuid;
  readonly name: string;
}

/**
 * Demanda como ela aparece na coluna de uma etapa.
 *
 * O cliente e o responsavel vem resolvidos em nome, diferente de `DemandRead`,
 * que entrega apenas `client_id` e `owner_id`: o quadro mostra dezenas de
 * cartoes de uma vez e nao teria como traduzir identificador em nome sem uma
 * consulta por cartao. `owner` e nulo quando ninguem assumiu a demanda.
 *
 * Nao ha `current_stage`: a etapa e a da coluna que contem o cartao.
 */
export interface PipelineCardRead {
  readonly id: Uuid;
  readonly title: string;
  readonly status: DemandStatus;
  readonly client: PipelineCardPersonRead;
  readonly owner: PipelineCardPersonRead | null;
  readonly created_at: IsoDateTime;
  readonly updated_at: IsoDateTime;
}

/**
 * Uma coluna do quadro.
 *
 * `total` conta todas as demandas da etapa que passam pelos filtros, nao
 * apenas as que vieram em `items` - o recorte por coluna tem teto (`limit`).
 * Por isso a coluna mostra o total do servidor, e nunca `items.length`.
 */
export interface PipelineStageGroup {
  readonly stage: PipelineStage;
  readonly total: number;
  readonly items: readonly PipelineCardRead[];
}

/**
 * Quadro completo: as cinco etapas, inclusive as vazias, e o total do recorte.
 *
 * A ordem das colunas e a que o servico devolve. A interface nao a recalcula:
 * a sequencia das etapas e regra de negocio do pipeline-service, e duplica-la
 * aqui criaria duas versoes da mesma regra para divergirem com o tempo.
 */
export interface PipelineBoard {
  readonly stages: readonly PipelineStageGroup[];
  readonly total: number;
}

/**
 * Filtros de `GET /api/v1/pipeline`, combinados com AND. Sao os mesmos da
 * listagem de demandas (RF03), menos `stage`: o agrupamento ja e por etapa, e
 * o servico recusa o parametro com 422 em vez de ignora-lo em silencio.
 *
 * `limit` corta cartoes por coluna e nao afeta o `total` de cada etapa.
 */
export interface PipelineBoardParams {
  readonly client_id?: Uuid;
  readonly owner_id?: Uuid;
  readonly status?: DemandStatus;
  readonly from?: IsoDateTime;
  readonly to?: IsoDateTime;
  readonly limit?: number;
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

// ---------------------------------------------------------------------------
// Resultado da IA anexado a demanda - DERIVADO de
// packages/contracts/openapi/pipeline-service.yaml
// (`ArtifactRead` e seus agregados: resposta de GET e de POST
//  /api/v1/demands/{demand_id}/artifacts)
// ---------------------------------------------------------------------------

/**
 * Fonte usada por um artefato, na forma em que o vinculo N:N a devolve.
 *
 * Traz so a referencia - identificador, canal e data. O texto de cada fonte
 * vem em `DemandRawInputRead`, no agregado do detalhe: o mesmo identificador
 * liga os dois, e e esse par que mostra na tela de revisao (RF19) qual texto
 * originou a estrutura gerada.
 */
export interface ArtifactSourceRead {
  readonly id: Uuid;
  readonly source: RawInputSource;
  readonly created_at: IsoDateTime;
}

/**
 * Versao do resultado anexado a demanda (RF13).
 *
 * `structured_content` e o curso ja validado contra o schema canonico pelo
 * servico (RNF03) - por isso chega como objeto JSON aberto e a tela o le sem
 * revalidar regra de negocio. `raw_output` e a resposta integral do modelo,
 * preservada para auditoria (RNF09).
 */
export interface ArtifactResultVersionRead {
  readonly id: Uuid;
  readonly number: number;
  readonly raw_output: string;
  readonly structured_content: JsonObject;
  readonly origin: ArtifactVersionOrigin;
  readonly ai_metadata: JsonObject | null;
  readonly created_at: IsoDateTime;
}

/**
 * Artefato recuperado pela demanda, com as fontes que o originaram e suas
 * versoes.
 *
 * E o que `GET /api/v1/demands/{demand_id}/artifacts` devolve: uma lista
 * simples, sem envelope de paginacao - o contrato nao pagina esta operacao.
 */
export interface ArtifactResultRead {
  readonly id: Uuid;
  readonly demand_id: Uuid;
  readonly type: ArtifactType;
  readonly title: string | null;
  readonly created_at: IsoDateTime;
  readonly sources: readonly ArtifactSourceRead[];
  readonly versions: readonly ArtifactResultVersionRead[];
}

// ---------------------------------------------------------------------------
// Curso estruturado - DERIVADO de
// packages/contracts/openapi/ai-structuring-service.yaml
// (`StructuredCourse`, `SyllabusModule`, `FieldGap`, `GapKind`, `CourseFormat`)
// ---------------------------------------------------------------------------

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
 * Apontamento de um campo que ficou sem valor utilizavel. `motivo` e nulo
 * quando o modelo nao registrou explicacao - a lacuna continua visivel na
 * revisao, so sem o porque.
 */
export interface FieldGap {
  readonly campo: string;
  readonly tipo: GapKind;
  readonly motivo: string | null;
}

/** Formatos de realizacao declarados pelo contrato (RF11). */
export const COURSE_FORMATS = ['presencial', 'online', 'hibrido'] as const;

export type CourseFormat = (typeof COURSE_FORMATS)[number];

/**
 * Modulo da ementa: um bloco de conteudo com titulo, topicos e carga (RF12).
 *
 * A ementa e lista de modulos, e nao lista de textos: cada modulo carrega a
 * propria carga horaria, e achatar isso em frase perderia a unica parte da
 * saida que da para conferir contra a carga total.
 */
export interface SyllabusModule {
  readonly titulo: string;
  readonly topicos: readonly string[];
  readonly carga_horaria: number | null;
}

/**
 * Saida canonica da estruturacao por IA (RF11, RF12).
 *
 * DERIVADO de `StructuredCourse` em
 * packages/contracts/openapi/ai-structuring-service.yaml. Valor nulo ou lista
 * vazia significa "nao ha valor utilizavel no texto de entrada", e o campo
 * correspondente aparece em `campos_ausentes`: o servico reconcilia os dois,
 * entao as duas leituras nunca se contradizem.
 *
 * `nicho`, `numero_participantes` e `formato` tem valor padrao no contrato e
 * por isso podem nao ser serializados; os demais sao obrigatorios na resposta.
 */
export interface StructuredCourse {
  readonly tema: string | null;
  readonly nicho?: string | null;
  readonly publico_alvo: string | null;
  readonly numero_participantes?: number | null;
  readonly carga_horaria: number | null;
  readonly formato?: CourseFormat | null;
  readonly objetivos_aprendizagem: readonly string[];
  readonly ementa: readonly SyllabusModule[];
  /**
   * Campo sem valor utilizavel no texto de entrada e apontado aqui, nunca
   * inferido (RF14). Cada item traz o campo, o tipo da lacuna e o motivo.
   */
  readonly campos_ausentes: readonly FieldGap[];
  readonly observacoes: readonly string[];
}

// ---------------------------------------------------------------------------
// Execucao da estruturacao - DERIVADO de
// packages/contracts/openapi/ai-structuring-service.yaml
// (`StructuringRequest`, `StructuringJobAccepted`, `StructuringJobRead`)
// ---------------------------------------------------------------------------

/**
 * Texto que entra na estruturacao (RF11, RF17).
 *
 * `demand_id` correlaciona log, metrica e reprocessamento; `text` e o texto da
 * demanda. `prompt_version` tem valor padrao no servico e por isso nao e
 * enviada: escolher versao de prompt e decisao de quem opera o modelo, nao da
 * tela.
 */
export interface StructuringRequest {
  readonly demand_id: string;
  readonly text: string;
  readonly prompt_version?: string;
}

/** Estados possiveis de uma execucao de estruturacao (RF24). */
export const JOB_STATUSES = ['PENDENTE', 'PROCESSANDO', 'CONCLUIDA', 'ERRO'] as const;

export type JobStatus = (typeof JOB_STATUSES)[number];

/** Confirmacao de que o pedido entrou na fila, sem esperar o resultado. */
export interface StructuringJobAccepted {
  readonly job_id: Uuid;
  readonly demand_id: string;
  readonly status: JobStatus;
  readonly created_at: IsoDateTime;
}

/** Falha que encerrou a execucao, no mesmo vocabulario do envelope (RNF02). */
export interface StructuringJobError {
  readonly code: string;
  readonly message: string;
}

/** Proveniencia da execucao que produziu o curso (RNF04, RNF09). */
export interface ExecutionMetadata {
  readonly provider: string;
  readonly model: string;
  readonly prompt: string;
  readonly attempts: number;
  readonly prompt_tokens: number;
  readonly completion_tokens: number;
  readonly total_tokens: number;
  readonly provider_latency_ms: number;
  readonly elapsed_ms: number;
}

/** Curso estruturado devolvido pela estruturacao, com a proveniencia. */
export interface StructuringResponse {
  readonly demand_id: string;
  readonly course: StructuredCourse;
  readonly execution: ExecutionMetadata;
}

/**
 * Estado da execucao e, quando houver, o que ela produziu.
 *
 * `result` vem nulo enquanto nao concluiu: nao existe curso parcial, e exibir
 * um esqueleto vazio faria a tela mostrar campos que ninguem preencheu
 * (RNF03). `total_elapsed_ms` mede do aceite ao desfecho - e o tempo que o
 * operador sente (RNF06).
 */
export interface StructuringJobRead {
  readonly job_id: Uuid;
  readonly demand_id: string;
  readonly status: JobStatus;
  readonly created_at: IsoDateTime;
  readonly started_at: IsoDateTime | null;
  readonly finished_at: IsoDateTime | null;
  readonly total_elapsed_ms: number | null;
  readonly result: StructuringResponse | null;
  readonly execution: ExecutionMetadata | null;
  readonly error: StructuringJobError | null;
}
