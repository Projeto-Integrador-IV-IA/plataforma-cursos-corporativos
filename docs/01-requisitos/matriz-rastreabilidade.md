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
| RF01 | Cadastrar/editar/consultar clientes | Essencial | pipeline | | 3 | 🟡 | RF01.1: `POST/GET /api/v1/clients`; `tests/unit/test_clients.py` |
| RF02 | Cadastrar demandas vinculadas a cliente | Essencial | pipeline | | 3 | ⬜ | |
| RF03 | Listar e filtrar por status, cliente e período | Alta | pipeline + web | | 3 | ⬜ | |
| RF04 | Detalhe da negociação com histórico e artefatos | Essencial | pipeline + web | | 3 | ⬜ | |
| RF05 | Percorrer as etapas do pipeline | Essencial | pipeline | | 3 | ⬜ | |
| RF06 | Retroceder livremente a etapas anteriores | Essencial | pipeline | | 3 | ⬜ | |
| RF07 | Histórico de alterações de etapa | Essencial | pipeline | | 3 | ⬜ | |
| RF08 | Versionar artefatos com recuperação | Alta | pipeline | | 3 | ⬜ | |
| RF09 | Inserir demanda como texto livre | Essencial | ingestion + web | | 3 | ⬜ | |
| RF10 | Normalizar a entrada bruta | Alta | ingestion | | 3 | ⬜ | |
| RF11 | Extrair requisitos do texto não estruturado | Essencial | ai-structuring | | 2 (PoC) / 3 | ⬜ | |
| RF12 | Gerar ementa com objetivos de aprendizagem | Essencial | ai-structuring | | 2 (PoC) / 3 | ⬜ | |
| RF13 | Anexar resultado estruturado à negociação | Essencial | ai + pipeline | | 3 | ⬜ | |
| RF14 | Revisar e editar a saída da IA | Essencial | web + pipeline | | 3 | ⬜ | |
| RF15 | Fonte única de verdade dos artefatos | Essencial | pipeline | | 3 | ⬜ | |
| RF16 | Autenticar o usuário | Alta | gateway | | 3 | ⬜ | |
| RF17 | Estado de processamento da IA | Alta | web + ingestion | | 3 | ⬜ | |

## Bloco A — Requisitos não funcionais

| ID | Requisito (resumo) | Prioridade | Card | Fase | Status | Evidência |
|---|---|---|---|---|---|---|
| RNF01 | Arquitetura em microsserviços | Essencial | | 2 | 🟡 | Estrutura criada; [ADR-0001](../02-arquitetura/decisoes/ADR-0001-arquitetura-microsservicos.md) |
| RNF02 | Contratos de API versionados | Alta | | 2 | 🟡 | Esqueleto em `packages/contracts` |
| RNF03 | Prompts com schema de saída definido | Essencial | | 2 | ⬜ | |
| RNF04 | Métricas de qualidade da estruturação | Alta | | 3 | ⬜ | |
| RNF05 | Falha/timeout do LLM sem perda da demanda | Essencial | | 3 | ⬜ | |
| RNF06 | Estruturação em tempo interativo (≤ 15 s) | Alta | | 3 | ⬜ | |
| RNF07 | CRUD do CRM ≤ 500 ms | Média | | 3 | ⬜ | |
| RNF08 | Integridade referencial no banco | Essencial | | 2 | ⬜ | |
| RNF09 | Trilha de auditoria íntegra | Essencial | | 3 | ⬜ | |
| RNF10 | Controle de acesso | Essencial | | 3 | ⬜ | |
| RNF11 | Segredos fora do código | Essencial | | 1 | ✅ | `.env.example` + job de segurança na CI |
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
