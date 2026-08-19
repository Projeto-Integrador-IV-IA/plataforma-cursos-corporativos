# Modelo de negócio enxuto

| Bloco | Definição |
|---|---|
| **Problema** | Processo de venda e produção de cursos corporativos fragmentado entre e-mail, reunião e WhatsApp, e centralizado em um único operador — gerando gargalo e retrabalho. |
| **Proposta de valor** | Consolidar todo o processo em uma plataforma única, com rastreabilidade ponta a ponta e estruturação automatizada das demandas, liberando capacidade do operador. |
| **Público** | Empresas de treinamento corporativo que vendem cursos sob demanda; o usuário direto é o profissional que conduz relacionamento, produto e proposta. |
| **Como a IA entra** | Modelo de linguagem estrutura demandas heterogêneas (e-mail, transcrição, mensagens) em produto de curso organizado — ementa, público, carga horária e objetivos. |
| **Custos** | Desenvolvimento acadêmico (custo próximo de zero); operação com consumo de API de linguagem e hospedagem em camada gratuita/estudantil. |
| **Receita / sustentação** | Modelo de assinatura da plataforma (SaaS) pela empresa cliente na continuidade comercial; no escopo acadêmico, sustentação via infraestrutura de baixo custo. |

## Validação: é um bom problema?

| Critério | Situação do projeto |
|---|---|
| Dor real e frequente, com público | **Sim** — cliente real com gargalo diário (2–3 propostas/dia); mercado de treinamento corporativo amplo. |
| Dados disponíveis | **Sim** — demandas, propostas e artefatos do próprio cliente; entrada textual heterogênea. |
| Cabe no prazo e na equipe | **Sim** — 6 integrantes, ~15 semanas, escopo modular e faseado. |
| A IA agrega valor real | **Sim** — estruturação de linguagem heterogênea não é resolvível por regra simples; interpretação exige modelo de linguagem. |
| Alguém pagaria pela solução | **Sim** — cliente real já demonstra a necessidade e opera o processo manualmente hoje. |

## Viabilidade

| Técnica | Econômica |
|---|---|
| Entrada textual disponível e estruturável. | Custo operacional baixo (API + hospedagem). |
| Equipe de 6 cobre backend, frontend e IA. | Público amplo no mercado de treinamento corporativo. |
| Modelo de linguagem atinge qualidade útil na estruturação. | Cliente real disposto a manter/adotar a solução. |
| Arquitetura em microsserviços viável e escalável. | Benefício (tempo liberado) supera o custo de operação. |
| Implantável como serviço web. | Sustentável como SaaS na continuidade comercial. |

> **Observação sobre a disciplina.** Por se tratar de projeto com cliente real, a equipe foi
> dispensada pelo professor da exigência de aprendizado supervisionado nos moldes gerais da
> disciplina. O núcleo de IA é a **estruturação por modelo de linguagem**, integrada em arquitetura
> de microsserviços.
