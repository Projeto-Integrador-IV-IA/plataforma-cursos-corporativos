# Matriz de rastreabilidade

Atende **RNF16**: rastreabilidade requisito → card → sprint.

Este é o documento vivo do projeto. **Atualize-o em todo PR** que avance um requisito — é ele que
mostra, em uma tela, onde o MVP está.

## Como preencher

| Coluna | Preenchimento |
|---|---|
| **Card** | Número da issue no GitHub Projects (`#12`). |
| **Fase** | Fase do cronograma em que o requisito é entregue. |
| **Status** | ⬜ não iniciado · 🟡 em andamento · ✅ concluído · ⛔ bloqueado |
| **Evidência** | Onde verificar: caminho do módulo, teste ou tela. |

## Bloco A — Requisitos funcionais

| ID | Requisito (resumo) | Prioridade | Serviço | Card | Fase | Status | Evidência |
|---|---|---|---|---|---|---|---|
| RF01 | Cadastrar/editar/consultar clientes | Essencial | pipeline | | 3 | ⬜ | Modelo `Client` já existe (RNF08); falta o CRUD. O PR #133 foi fechado sem merge — ao retomar, reutilizar o modelo e a fábrica de sessões atuais, sem recriar a tabela |
| RF02 | Cadastrar demandas vinculadas a cliente | Essencial | pipeline | #149 | 3 | 🟡 | `POST /api/v1/demands` em [`routes/demands.py`](../../services/pipeline-service/app/api/v1/routes/demands.py) e [`demand_service.py`](../../services/pipeline-service/app/services/demand_service.py): cliente obrigatório e existente, demanda nasce `ABERTA` em `CAPTACAO`. Contrato em [`pipeline-service.yaml`](../../packages/contracts/openapi/pipeline-service.yaml), migration `20260916_1200` (título não vazio) e testes em [`test_demands.py`](../../services/pipeline-service/tests/integration/test_demands.py). Exige um cliente já persistido (RF01); edição e consulta pendentes |
| RF03 | Listar e filtrar por status, cliente e período | Alta | pipeline + web | | 3 | ⬜ | |
| RF04 | Detalhe da negociação com histórico e artefatos | Essencial | pipeline + web | | 3 | ⬜ | |
| RF05 | Percorrer as etapas do pipeline | Essencial | pipeline | #148 | 3 | 🟡 | Máquina de estados em [`app/domain/rules.py`](../../services/pipeline-service/app/domain/rules.py) (avanço só para a etapa seguinte); etapa inicial garantida pelo schema, em [`test_demand_state.py`](../../services/pipeline-service/tests/integration/test_demand_state.py); transições cobertas em [`test_pipeline_rules.py`](../../services/pipeline-service/tests/unit/test_pipeline_rules.py). Rotas e persistência da transição (RF07) pendentes |
| RF06 | Retroceder livremente a etapas anteriores | Essencial | pipeline | #148 | 3 | 🟡 | Retrocesso para qualquer etapa anterior na mesma máquina de estados ([`app/domain/rules.py`](../../services/pipeline-service/app/domain/rules.py)), com os 25 pares de etapas verificados em [`test_pipeline_rules.py`](../../services/pipeline-service/tests/unit/test_pipeline_rules.py). Rotas pendentes |
| RF07 | Histórico de alterações de etapa | Essencial | pipeline | | 3 | ⬜ | |
| RF08 | Versionar artefatos com recuperação | Alta | pipeline | | 3 | ⬜ | |
| RF09 | Inserir demanda como texto livre | Essencial | ingestion + web | | 3 | ⬜ | |
| RF10 | Normalizar a entrada bruta | Alta | ingestion | | 3 | ⬜ | |
| RF11 | Extrair requisitos do texto não estruturado | Essencial | ai-structuring | #5 | 2 (PoC) / 3 | 🟡 | Prompt versionado [`extract-requirements.v1.md`](../../services/ai-structuring-service/app/prompts/extract-requirements.v1.md), carregado por versão em [`app/prompts/__init__.py`](../../services/ai-structuring-service/app/prompts/__init__.py); testes em [`test_prompts.py`](../../services/ai-structuring-service/tests/unit/test_prompts.py) e [`test_extract_requirements.py`](../../services/ai-structuring-service/tests/integration/test_extract_requirements.py). Caso de uso e validação de schema pendentes |
| RF12 | Gerar ementa com objetivos de aprendizagem | Essencial | ai-structuring | | 2 (PoC) / 3 | ⬜ | |
| RF13 | Anexar resultado estruturado à negociação | Essencial | ai + pipeline | | 3 | ⬜ | |
| RF14 | Revisar e editar a saída da IA | Essencial | web + pipeline | | 3 | ⬜ | |
| RF15 | Fonte única de verdade dos artefatos | Essencial | pipeline | | 3 | ⬜ | |
| RF16 | Autenticar o usuário | Alta | gateway | | 3 | ⬜ | |
| RF17 | Estado de processamento da IA | Alta | web + ingestion | | 3 | ⬜ | |

## Bloco A — Requisitos não funcionais

| ID | Requisito (resumo) | Prioridade | Card | Fase | Status | Evidência |
|---|---|---|---|---|---|---|
| RNF01 | Arquitetura em microsserviços | Essencial | #141, #84 | 2 | 🟡 | Estrutura criada; [ADR-0001](../02-arquitetura/decisoes/ADR-0001-arquitetura-microsservicos.md). Composição em [`docker-compose.yml`](../../docker-compose.yml): rede privada, só o gateway expõe porta, healthcheck por serviço ([topologia](../../infra/docker/README.md)). Os quatro backends sobem com `create_app()` e `GET /health`, testados em `tests/unit/test_health.py`; `GET /ready` e rotas de negócio pendentes. Frontend: [`web/src/app/routes.tsx`](../../web/src/app/routes.tsx), teste em [`web/src/app/routes.test.tsx`](../../web/src/app/routes.test.tsx). Mensagem unica de sucesso e erro para todas as telas em [`web/src/components/FeedbackProvider.tsx`](../../web/src/components/FeedbackProvider.tsx) e [`web/src/components/FeedbackMessage.tsx`](../../web/src/components/FeedbackMessage.tsx), disparada de qualquer tela por [`web/src/hooks/useFeedback.ts`](../../web/src/hooks/useFeedback.ts) e testada em [`web/src/components/FeedbackProvider.test.tsx`](../../web/src/components/FeedbackProvider.test.tsx) — card #84, que cita **RF25** do Documento Consolidado de Requisitos v1.0; esta matriz não tem requisito equivalente, então a evidência fica aqui até a equipe decidir se cria a linha |
| RNF02 | Contratos de API versionados | Alta | | 2 | 🟡 | Esqueleto em `packages/contracts` |
| RNF03 | Prompts com schema de saída definido | Essencial | #3, #4 | 2 | 🟡 | Contrato em [`providers/base.py`](../../services/ai-structuring-service/app/providers/base.py), erros tipados em [`core/exceptions.py`](../../services/ai-structuring-service/app/core/exceptions.py) e provedores `mock`/`http` selecionados por `LLM_PROVIDER` ([`providers/factory.py`](../../services/ai-structuring-service/app/providers/factory.py)); testes em [`tests/unit`](../../services/ai-structuring-service/tests/unit). Prompts e validação de schema pendentes |
| RNF04 | Métricas de qualidade da estruturação | Alta | | 3 | ⬜ | |
| RNF05 | Falha/timeout do LLM sem perda da demanda | Essencial | | 3 | ⬜ | |
| RNF06 | Estruturação em tempo interativo (≤ 15 s) | Alta | | 3 | ⬜ | |
| RNF07 | CRUD do CRM ≤ 500 ms | Média | | 3 | ⬜ | |
| RNF08 | Integridade referencial no banco | Essencial | #136, #137 | 2 | ✅ | Migration [`20260902_1200_enforce_referential_integrity.py`](../../services/pipeline-service/app/db/migrations/versions/20260902_1200_enforce_referential_integrity.py); modelos ORM em [`app/models/`](../../services/pipeline-service/app/models/); sessão em [`app/db/session.py`](../../services/pipeline-service/app/db/session.py); testes em [`test_referential_integrity.py`](../../services/pipeline-service/tests/integration/test_referential_integrity.py), [`test_models.py`](../../services/pipeline-service/tests/unit/test_models.py) e [`test_session.py`](../../services/pipeline-service/tests/unit/test_session.py) |
| RNF09 | Trilha de auditoria íntegra | Essencial | | 3 | 🟡 | Tabelas `stage_transitions` e `artifact_versions` criadas; `REVOKE UPDATE, DELETE` pendente |
| RNF10 | Controle de acesso | Essencial | | 3 | ⬜ | |
| RNF11 | Segredos fora do código | Essencial | | 1 | ✅ | `Settings` por ambiente + `SecretStr` + hash bcrypt + scanner na CI |
| RNF12 | Operação em camada gratuita | Alta | | 3 | ⬜ | |
| RNF13 | Serviços desacoplados | Alta | | 2 | 🟡 | [ADR-0001](../02-arquitetura/decisoes/ADR-0001-arquitetura-microsservicos.md) |
| RNF14 | Fluxo Card → PR → Merge no GitHub | Alta | | 1 | ✅ | [CONTRIBUTING.md](../../CONTRIBUTING.md), templates, CI |
| RNF15 | Portabilidade como serviço web | Média | | 4 | ⬜ | |
| RNF16 | Rastreabilidade no GitHub Projects | Média | | 1 | 🟡 | Este documento + templates de issue |

## Cobertura por serviço

| Serviço | Requisitos sob sua responsabilidade |
|---|---|
| `gateway-service` | RF16, RF17, RNF02, RNF10 |
| `pipeline-service` | RF01–RF08, RF13, RF14, RF15, RNF07, RNF08, RNF09 |
| `ingestion-service` | RF09, RF10, RF17, RNF05 |
| `ai-structuring-service` | RF11, RF12, RF13, RNF03, RNF04, RNF05, RNF06, RNF12 |
| `web` | RF03, RF04, RF05, RF06, RF09, RF14, RF17 |
| Processo / repositório | RNF11, RNF13, RNF14, RNF15, RNF16 |

## Bloco B — Evoluções futuras

Fora do escopo desta disciplina. Não recebem card nem entram em sprint:
`RF-F1` a `RF-F5`, `RNF-F1` a `RNF-F3`.
