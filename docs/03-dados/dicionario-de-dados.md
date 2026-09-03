# Dicionário de dados

Definição campo a campo das tabelas descritas em [modelo-dados.md](modelo-dados.md).

> **Estado:** tipos e restrições de integridade implementados pela migration
> [`20260902_1200_enforce_referential_integrity.py`](../../services/pipeline-service/app/db/migrations/versions/20260902_1200_enforce_referential_integrity.py)
> (RNF14 do Documento Consolidado de Requisitos v1.0). Toda alteração aqui exige migration
> correspondente.

**Convenções gerais**

- Chaves primárias são `uuid`, geradas com `gen_random_uuid()` (extensão `pgcrypto`).
- Timestamps são `timestamptz`, em UTC; a interface converte para America/Sao_Paulo.
- `created_at` e `updated_at` são preenchidos pelo banco.
- Campos de texto livre usam `text`, não `varchar(n)` arbitrário.

---

## `users` — operadores da plataforma (RF16)

| Campo | Tipo | Nulo | Descrição |
|---|---|---|---|
| `id` | uuid PK | não | Identificador. |
| `name` | text | não | Nome do operador. |
| `email` | text UNIQUE | não | Login. |
| `password_hash` | text | não | Hash da senha. **Nunca em texto claro** (RNF10, RNF11). |
| `role` | text | não | `OPERADOR` no MVP. Ver [Q6](../01-requisitos/questoes-em-aberto.md#q6--papéis-de-usuário). |
| `active` | boolean | não | Desativação lógica; usuário não é apagado. |
| `created_at` | timestamptz | não | |

---

## `clients` — empresas clientes (RF01)

| Campo | Tipo | Nulo | Descrição |
|---|---|---|---|
| `id` | uuid PK | não | |
| `name` | text | não | Razão social ou nome corporativo. |
| `cnpj` | text | sim | Opcional; único quando informado. |
| `segment` | text | sim | Setor/nicho de atuação — insumo da estruturação (RF11). |
| `contact_name` | text | sim | Contato principal. |
| `contact_email` | text | sim | |
| `contact_phone` | text | sim | |
| `notes` | text | sim | Notas livres do operador. |
| `active` | boolean | não | Desativação lógica. |
| `created_at` / `updated_at` | timestamptz | não | |

---

## `demands` — negociações (RF02)

| Campo | Tipo | Nulo | Descrição |
|---|---|---|---|
| `id` | uuid PK | não | |
| `client_id` | uuid FK → `clients.id` | **não** | Integridade referencial (RNF08). Toda demanda tem cliente. |
| `title` | text | não | Identificação curta da negociação. |
| `description` | text | sim | Contexto adicional. |
| `current_stage` | text | não | `CAPTACAO`, `ESTRUTURACAO`, `PRODUTO`, `PROPOSTA`, `ACOMPANHAMENTO`. Desnormalizado — ver [decisão 1](modelo-dados.md#1-etapa-corrente-duplicada--de-propósito). |
| `status` | text | não | `ABERTA`, `GANHA`, `PERDIDA`, `CANCELADA`. |
| `owner_id` | uuid FK → `users.id` | sim | Responsável pela negociação. |
| `active` | boolean | não | Desativação lógica. |
| `created_at` / `updated_at` | timestamptz | não | |

---

## `raw_inputs` — demanda bruta (RF09, RF10)

| Campo | Tipo | Nulo | Descrição |
|---|---|---|---|
| `id` | uuid PK | não | |
| `demand_id` | uuid FK → `demands.id` | não | |
| `original_content` | text | **não** | Texto exatamente como chegou. **Nunca alterado** — é a garantia de RNF05. |
| `normalized_content` | text | sim | Resultado de RF10. Nulo enquanto não normalizado. |
| `source` | text | não | `EMAIL`, `TRANSCRICAO`, `MENSAGENS`, `ANOTACAO`, `OUTRO`. |
| `truncated` | boolean | não | Indica corte por limite de tamanho na normalização. |
| `author_id` | uuid FK → `users.id` | não | Quem registrou. |
| `created_at` | timestamptz | não | |

---

## `stage_transitions` — histórico de etapas (RF07, RNF09)

**Append-only.** Sem UPDATE, sem DELETE.

| Campo | Tipo | Nulo | Descrição |
|---|---|---|---|
| `id` | uuid PK | não | |
| `demand_id` | uuid FK → `demands.id` | não | |
| `from_stage` | text | sim | Nulo apenas na criação da demanda (entrada em `CAPTACAO`). |
| `to_stage` | text | não | Etapa de destino. |
| `reason` | text | sim | **Obrigatório no retrocesso** (RF06); opcional no avanço. |
| `author_id` | uuid FK → `users.id` | não | Vem do token autenticado, nunca do corpo da requisição. |
| `occurred_at` | timestamptz | não | Instante da transição. |

---

## `artifacts` — documentos da negociação (RF15)

| Campo | Tipo | Nulo | Descrição |
|---|---|---|---|
| `id` | uuid PK | não | |
| `demand_id` | uuid FK → `demands.id` | não | Fonte única de verdade: todo artefato pertence a uma negociação. |
| `type` | text | não | `DEMANDA_BRUTA`, `REQUISITOS_EXTRAIDOS`, `EMENTA`, `PROPOSTA`, `OUTRO`. |
| `title` | text | sim | Rótulo exibido ao operador. |
| `raw_input_id` | uuid FK → `raw_inputs.id` | sim | Quando informado, a FK composta com `demand_id` exige que a fonte pertença à mesma demanda do artefato. |
| `created_at` | timestamptz | não | |

---

## `artifact_versions` — versões (RF08, RNF09)

**Append-only.** Editar cria linha nova; versão anterior permanece recuperável.

| Campo | Tipo | Nulo | Descrição |
|---|---|---|---|
| `id` | uuid PK | não | |
| `artifact_id` | uuid FK → `artifacts.id` | não | |
| `number` | integer | não | Sequencial por artefato, começando em 1. Único com `artifact_id`. |
| `content` | jsonb | não | Conteúdo da versão. Para curso estruturado, valida contra o JSON Schema (RNF03). |
| `origin` | text | não | `IA` ou `HUMANO`. Distingue o gerado do revisado (RF14) — base da métrica de correção (RNF04). |
| `ai_metadata` | jsonb | sim | Modelo, versão de prompt, tokens de entrada e saída, latência. Preenchido quando `origin = IA`. |
| `author_id` | uuid FK → `users.id` | sim | Nulo quando gerado pela IA sem intervenção. |
| `created_at` | timestamptz | não | |

### Estrutura de `ai_metadata`

```json
{
  "modelo": "...",
  "versao_prompt": "extract-requirements.v1",
  "tokens_entrada": 0,
  "tokens_saida": 0,
  "latencia_ms": 0,
  "tentativas": 1
}
```

Sem esses metadados, um resultado não é reproduzível nem auditável, e as métricas de RNF04 não podem
ser recalculadas depois.

---

## Restrições que valem a pena reforçar no banco

| Restrição | Requisito |
|---|---|
| `REVOKE UPDATE, DELETE` em `stage_transitions` e `artifact_versions` para o usuário da aplicação | RNF09 |
| `UNIQUE (artifact_id, number)` | RF08 — numeração sem lacuna nem duplicata |
| `NOT NULL` em `demands.client_id` | RNF14 — demanda órfã não existe |
| `FOREIGN KEY (raw_input_id, demand_id)` em `artifacts` | RNF14 — artefato não referencia fonte de outra demanda |
| `CHECK` nos campos de enum (`current_stage`, `status`, `type`, `origin`) | Vocabulário fechado é contrato |
| `NOT NULL` em `raw_inputs.original_content` | RNF05 — o bruto sempre existe |
