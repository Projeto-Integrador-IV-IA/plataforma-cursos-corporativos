# Plano de ação 5W2H

## Visão geral do projeto

| Dimensão | Definição |
|---|---|
| **What** | Desenvolver documentação e MVP funcional de plataforma de consolidação, rastreabilidade e estruturação por IA de cursos corporativos, em arquitetura de microsserviços. |
| **Why** | Eliminar a fragmentação de um processo hoje disperso em múltiplos canais e centralizado em um único operador, reduzindo tempo de ciclo e dependência operacional. |
| **Who** | Equipe de 6: gerência, documentação, backend (2), IA e frontend (2). |
| **Where** | Repositório GitHub, GitHub Projects e ambiente de desenvolvimento web; homologação junto ao cliente. |
| **When** | 18/08 a 24/11/2026, em quatro fases alinhadas às entregas parciais (25/08, 15/09, 20/10, 17/11) e banca em 24/11. |
| **How** | Metodologia Scrum, frentes paralelas, integração incremental e revisão humana dos artefatos gerados pela IA. |
| **How much** | Custo próximo de zero; consumo de API de linguagem como única despesa recorrente; infraestrutura em camada gratuita/estudantil. |

---

## Fase 1 — Concepção e planejamento (18/08 a 25/08)

| Atividade | Responsável | Prazo | Método |
|---|---|---|---|
| Consolidar escopo, problema, público e requisitos iniciais | Documentação | 18–25/08 | Revisão e consolidação em documento único |
| Preencher modelo de negócio e validação de viabilidade | Documentação + Gerência | 18–25/08 | Quadros no formato da disciplina |
| Definir stack tecnológica e configurar ambiente | Gerência + Backend | 18–25/08 | Reunião técnica; setup de repositório e GitHub Projects |
| Elaborar plano de ação e distribuir tarefas | Gerência | 22–25/08 | 5W2H e criação de cards no board |
| **1a entrega parcial** | Gerência | **25/08** | Submissão dos artefatos |

## Fase 2 — Modelagem e prova de conceito (26/08 a 15/09)

| Atividade | Responsável | Prazo | Método |
|---|---|---|---|
| Detalhar requisitos funcionais e não funcionais | Documentação + Backend | 26/08–05/09 | Especificação de requisitos e casos de uso |
| Modelar dados (cliente, demanda, etapa, artefato) | Backend | 26/08–08/09 | Modelo entidade-relacionamento e diagramas |
| Desenhar arquitetura de microsserviços | IA + Backend | 01–10/09 | Definição de serviços, APIs e fluxo de dados |
| Coletar insumos do cliente (proposta real, agentes atuais) | Gerência | paralelo | Contato e obtenção de artefatos reais |
| PoC inicial da estruturação por IA | IA | 05–15/09 | Integração com serviço de linguagem; testes com exemplos |
| **2a entrega parcial** | Gerência | **15/09** | Submissão de modelagem, arquitetura e PoC |

## Fase 3 — Desenvolvimento e integração (16/09 a 20/10)

| Atividade | Responsável | Prazo | Método |
|---|---|---|---|
| Implementar backend base (API + persistência) | Backend | 16/09–03/10 | Entidades, endpoints e camada de dados |
| Desenvolver módulo de cadastro de clientes e demandas | Frontend | 16/09–03/10 | Telas integradas à API |
| Construir pipeline com rastreabilidade e retrocesso | Frontend + Backend | 22/09–17/10 | Componente de pipeline, histórico e versionamento |
| Evoluir módulo de estruturação por IA e integrá-lo | IA | 16/09–17/10 | Refino de prompts; vínculo ao registro de demanda |
| Definir e medir métricas de qualidade da estruturação | IA + Documentação | 06–17/10 | Avaliação de acurácia/consistência da saída |
| Levantar custos de operação (API, hospedagem) | Gerência | 06–17/10 | Estimativa de consumo e infraestrutura |
| **3a entrega parcial** | Gerência | **20/10** | Submissão de backend, pipeline e métricas |

## Fase 4 — Integração final e validação (21/10 a 24/11)

| Atividade | Responsável | Prazo | Método |
|---|---|---|---|
| Integrar todos os microsserviços end-to-end | Backend + Frontend + IA | 21/10–07/11 | Testes de fluxo completo entre serviços |
| Testar, tratar exceções e ajustar | Equipe | 28/10–14/11 | Testes de cenário e correção de defeitos |
| Redigir relatório técnico e preparar apresentação | Documentação + Gerência | 03–21/11 | Consolidação documental e roteiro de demonstração |
| **4a entrega parcial (MVP funcional)** | Gerência | **17/11** | Submissão do MVP integrado |
| Pré-banca | Equipe | 22/09 | Validação intermediária com a banca |
| Homologação final e ensaio da apresentação | Equipe | 17–23/11 | Validação end-to-end e ensaio |
| **Banca** | Equipe | **24/11** | Apresentação final do projeto |
