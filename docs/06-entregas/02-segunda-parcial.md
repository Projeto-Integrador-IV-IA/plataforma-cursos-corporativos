# 2ª parcial — 15/09

**Marco M2** — Requisitos detalhados, modelagem de dados, arquitetura de microsserviços e prova de
conceito inicial da estruturação por IA.

## Requisitos detalhados

- [ ] RF e RNF revisados e detalhados
- [ ] Casos de uso do operador documentados
- [ ] Critérios de aceite escritos para todo card da Fase 3

## Modelagem de dados (até 08/09)

- [ ] Modelo entidade-relacionamento completo — [modelo de dados](../03-dados/modelo-dados.md)
- [ ] Dicionário de dados campo a campo — [dicionário](../03-dados/dicionario-de-dados.md)
- [ ] Integridade referencial entre cliente, demanda, etapa e artefato garantida (RNF08)
- [ ] Estratégia de trilha de auditoria definida (RNF09)
- [ ] Máquina de estados do pipeline validada, incluindo o retrocesso (RF05, RF06)
- [ ] Migrations iniciais escritas e testadas nos dois sentidos

## Arquitetura (até 10/09)

- [ ] Serviços, responsabilidades e fronteiras definidos — [visão geral](../02-arquitetura/visao-geral.md)
- [ ] Fluxo de dados entre serviços diagramado
- [ ] Contratos OpenAPI com os caminhos declarados (RNF02)
- [ ] Formato único de erro definido
- [ ] ADRs escritos e aceitos — [decisões](../02-arquitetura/decisoes)

## PoC da estruturação por IA (05–15/09)

- [ ] Integração com o serviço de linguagem funcionando
- [ ] Schema de saída definido — [`structured-course.schema.json`](../../packages/contracts/schemas/structured-course.schema.json)
- [ ] Prompt de extração `v1` escrito (RF11)
- [ ] Prompt de geração de ementa `v1` escrito (RF12)
- [ ] Teste com exemplos reais do cliente, anonimizados
- [ ] Latência medida — confronto com o alvo de RNF06
- [ ] Consumo de tokens medido — insumo do custo (RNF12)
- [ ] Métricas de qualidade **definidas** (RNF04) — [métricas](../04-ia/metricas-qualidade.md)

## Insumos do cliente

- [ ] Proposta comercial real obtida
- [ ] Exemplos de demanda bruta coletados e anonimizados
- [ ] Fluxo atual do operador mapeado

## Questões a fechar nesta fase

- [ ] **[Q1](../01-requisitos/questoes-em-aberto.md#q1--revisão--versionamento-de-artefato)** — revisão × versionamento (afeta a modelagem; fechar antes da Fase 3)
- [ ] **[Q2](../01-requisitos/questoes-em-aberto.md#q2--metas-de-desempenho)** — metas de desempenho reajustadas após medição
- [ ] **[Q3](../01-requisitos/questoes-em-aberto.md#q3--definição-da-métrica-de-qualidade-da-ia)** — métricas de qualidade definidas
- [ ] **[Q6](../01-requisitos/questoes-em-aberto.md#q6--papéis-de-usuário)** — papéis de usuário

## Pré-banca (22/09)

- [ ] Apresentação do problema, escopo e arquitetura preparada
- [ ] Demonstração da PoC ensaiada
- [ ] Riscos e questões em aberto explicitados — banca valoriza consciência de risco
