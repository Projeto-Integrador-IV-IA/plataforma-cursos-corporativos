# Requisitos funcionais

## Convenção

Os requisitos estão divididos em dois blocos:

- **Bloco A (MVP)** — requisitos detalhados que compõem a entrega funcional end-to-end até 17/11.
  São a base das tasks das sprints.
- **Bloco B (Evoluções futuras)** — requisitos das fases pós-MVP em nível macro, tratados como
  roadmap comercial e **não escopados** para implementação nesta disciplina.

**Prefixos:** `RF` = requisito funcional · `RF-F` = requisito funcional de fase futura.

**Prioridade:** `Essencial` (bloqueia o MVP) · `Alta` (necessário à qualidade da entrega) ·
`Média` (desejável; cortável sob pressão de prazo).

---

## Bloco A — Requisitos do MVP

### Cadastro e gestão de entidades

| ID | Requisito | Prioridade | Serviço |
|---|---|---|---|
| **RF01** | Cadastrar, editar e consultar empresas clientes. | Essencial | `pipeline-service` |
| **RF02** | Cadastrar demandas/negociações vinculadas a um cliente. | Essencial | `pipeline-service` |
| **RF03** | Listar e filtrar clientes e demandas por status, cliente e período. | Alta | `pipeline-service` + `web` |
| **RF04** | Visualizar o detalhe de uma negociação com histórico e artefatos atrelados. | Essencial | `pipeline-service` + `web` |

### Pipeline e rastreabilidade

| ID | Requisito | Prioridade | Serviço |
|---|---|---|---|
| **RF05** | Percorrer a negociação pelas etapas do pipeline: captação → estruturação → produto → proposta → acompanhamento. | Essencial | `pipeline-service` |
| **RF06** | Retroceder livremente a etapas anteriores quando o cliente altera escopo ou proposta. | Essencial | `pipeline-service` |
| **RF07** | Registrar histórico de alterações de etapa (quem, quando, estado de origem e destino). | Essencial | `pipeline-service` |
| **RF08** | Versionar os artefatos gerados, mantendo versões anteriores recuperáveis. | Alta | `pipeline-service` |

### Ingestão de demanda heterogênea

| ID | Requisito | Prioridade | Serviço |
|---|---|---|---|
| **RF09** | Inserir demanda como texto livre (e-mail colado, transcrição de reunião, mensagens) via formulário padronizado. | Essencial | `ingestion-service` + `web` |
| **RF10** | Normalizar e preparar a entrada bruta para envio à camada de IA. | Alta | `ingestion-service` |

### Estruturação por IA (núcleo inteligente)

| ID | Requisito | Prioridade | Serviço |
|---|---|---|---|
| **RF11** | Extrair requisitos da entrada não estruturada: tema, nicho, público-alvo, nº de participantes, carga horária e formato. | Essencial | `ai-structuring-service` |
| **RF12** | Gerar ementa com objetivos de aprendizagem a partir dos requisitos extraídos. | Essencial | `ai-structuring-service` |
| **RF13** | Anexar automaticamente o resultado estruturado ao registro da negociação. | Essencial | `ai-structuring-service` + `pipeline-service` |
| **RF14** | Permitir que o operador revise e edite a saída da IA antes de qualquer uso externo. | Essencial | `web` + `pipeline-service` |

### Consolidação documental

| ID | Requisito | Prioridade | Serviço |
|---|---|---|---|
| **RF15** | Manter todos os artefatos de uma negociação atrelados, versionados e recuperáveis em um único lugar (fonte única de verdade). | Essencial | `pipeline-service` |

### Acesso e operação

| ID | Requisito | Prioridade | Serviço |
|---|---|---|---|
| **RF16** | Autenticar o usuário para acessar a plataforma e seus registros. | Alta | `gateway-service` |
| **RF17** | Exibir estado de processamento durante a chamada de estruturação por IA (feedback de execução). | Alta | `web` + `ingestion-service` |

---

## Bloco B — Evoluções futuras

Requisitos das fases pós-MVP, tratados no documento de escopo comercial completo. **Não estão
escopados para implementação na disciplina.** Estão registrados aqui para preservar a coerência do
roadmap e justificar a decisão de arquitetura desacoplada (RNF13) que os viabiliza.

O reposicionamento do custeio — de núcleo original para evolução futura — decorre da constatação de
que **não existe base de custo modelável**: a estimativa é hoje tácita e humana.

| ID | Requisito | Prioridade |
|---|---|---|
| **RF-F1** | Sugestão orçamentária por faixas, condicionada à existência prévia de base de custo modelável. | Média |
| **RF-F2** | Geração automática da proposta comercial a partir do curso estruturado. | Média |
| **RF-F3** | Geração automática da apresentação comercial (slides). | Média |
| **RF-F4** | Busca e qualificação de instrutores, dependente de fontes e integrações externas. | Média |
| **RF-F5** | Integrações externas (e-mail, LinkedIn) e automação de prospecção. | Média |

> Implementar item do Bloco B durante o MVP é **desvio de escopo**. Se a necessidade aparecer, ela
> passa pela gerência antes de virar card.
