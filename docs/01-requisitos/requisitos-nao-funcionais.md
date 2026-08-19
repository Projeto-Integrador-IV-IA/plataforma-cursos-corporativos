# Requisitos não funcionais

**Prefixos:** `RNF` = requisito não funcional · `RNF-F` = requisito não funcional de fase futura.

**Prioridade:** `Essencial` (bloqueia o MVP) · `Alta` (necessário à qualidade da entrega) ·
`Média` (desejável; cortável sob pressão de prazo).

---

## Bloco A — Requisitos do MVP

### Arquitetura e integração

| ID | Requisito | Prioridade | Onde se materializa |
|---|---|---|---|
| **RNF01** | Arquitetura em microsserviços independentes comunicando-se por API: ingestão/normalização, estruturação (IA), pipeline/persistência e frontend web. | Essencial | [`services/`](../../services), [ADR-0001](../02-arquitetura/decisoes/ADR-0001-arquitetura-microsservicos.md) |
| **RNF02** | Contratos de API versionados e documentados entre os serviços. | Alta | [`packages/contracts/`](../../packages/contracts) |
| **RNF13** | Serviços desacoplados, permitindo evolução independente (custeio, instrutores, integrações) sem reescrita do núcleo. | Alta | [ADR-0001](../02-arquitetura/decisoes/ADR-0001-arquitetura-microsservicos.md) |

### IA e qualidade da estruturação

| ID | Requisito | Prioridade | Onde se materializa |
|---|---|---|---|
| **RNF03** | Prompts estruturados que garantam saída consistente em formato previsível (schema de saída definido). | Essencial | [`structured-course.schema.json`](../../packages/contracts/schemas/structured-course.schema.json), [catálogo de prompts](../../services/ai-structuring-service/app/prompts/README.md) |
| **RNF04** | Métricas de qualidade da estruturação (acurácia e consistência) mensuráveis e reportáveis — insumo da 3ª parcial. | Alta | [métricas de qualidade](../04-ia/metricas-qualidade.md) |
| **RNF05** | Tratamento de falha/timeout da chamada ao LLM sem perda da demanda bruta já registrada. | Essencial | `ingestion-service` (persiste antes de chamar o LLM) |

### Desempenho

| ID | Requisito | Prioridade | Alvo |
|---|---|---|---|
| **RNF06** | Estruturação por IA com resposta útil em tempo interativo, com estado de processamento visível (ver RF17). | Alta | ≤ 15 s por demanda |
| **RNF07** | Operações de CRUD do CRM com resposta perceptivelmente imediata. | Média | ≤ 500 ms em condição normal |

> Os alvos numéricos são **ponto de partida**. Devem ser reajustados após a PoC da 2ª parcial,
> quando houver medição real — ver [questões em aberto](questoes-em-aberto.md).

### Persistência e integridade

| ID | Requisito | Prioridade | Onde se materializa |
|---|---|---|---|
| **RNF08** | Banco relacional garantindo integridade referencial entre cliente, demanda, etapa e artefato. | Essencial | [modelo de dados](../03-dados/modelo-dados.md) |
| **RNF09** | Nenhuma transição de etapa ou versão de artefato pode ser perdida — trilha de auditoria íntegra. | Essencial | Tabelas `stage_transitions` e `artifact_versions`, append-only |

### Segurança

| ID | Requisito | Prioridade | Onde se materializa |
|---|---|---|---|
| **RNF10** | Controle de acesso à plataforma; dados de clientes não expostos publicamente. | Essencial | `gateway-service` |
| **RNF11** | Chaves de API e segredos mantidos fora do código-fonte (variáveis de ambiente). | Essencial | [`.env.example`](../../.env.example), job de segurança da CI |

### Custo e infraestrutura

| ID | Requisito | Prioridade | Observação |
|---|---|---|---|
| **RNF12** | Operação em camada gratuita/estudantil; consumo de API de linguagem como única despesa recorrente controlada. | Alta | Ver [custos de operação](../04-ia/custos-operacao.md) |
| **RNF15** | Portabilidade: implantável como serviço web em ambiente padrão. | Média | Containers, sem dependência de recurso proprietário |

### Manutenibilidade e processo

| ID | Requisito | Prioridade | Onde se materializa |
|---|---|---|---|
| **RNF14** | Versionamento em GitHub com fluxo Card → Branch → Commits → Pull Request → Review → Merge. | Alta | [fluxo Git](../05-processo/fluxo-git.md), [CI](../../.github/workflows/ci.yml) |
| **RNF16** | Rastreabilidade requisito → card → sprint mantida no GitHub Projects. | Média | [matriz de rastreabilidade](matriz-rastreabilidade.md), templates de issue |

---

## Bloco B — Evoluções futuras

| ID | Requisito | Prioridade |
|---|---|---|
| **RNF-F1** | Fundação de dados para custeio: coleta e estruturação de histórico de custos até tornar a estimativa modelável. | Média |
| **RNF-F2** | Camada de integração externa com gestão segura de credenciais de terceiros (OAuth e afins). | Média |
| **RNF-F3** | Escalabilidade multiusuário/multiempresa compatível com o modelo de assinatura (SaaS). | Média |
