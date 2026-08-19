# Documentação do projeto

Plataforma inteligente para consolidação, rastreabilidade e estruturação de cursos corporativos.
Projeto Integrador de Extensão IV · Curso IA/CD · Equipe de 6.

## Como navegar

| Pasta | Conteúdo | Responsável |
|---|---|---|
| [00-produto](00-produto) | Escopo do MVP, modelo de negócio, plano de ação 5W2H e cronograma. | Documentação + Gerência |
| [01-requisitos](01-requisitos) | RF e RNF detalhados, matriz de rastreabilidade, glossário e questões em aberto. | Documentação + Backend |
| [02-arquitetura](02-arquitetura) | Visão da arquitetura, diagramas, contratos de API e decisões (ADRs). | Backend + IA |
| [03-dados](03-dados) | Modelo de dados e dicionário de dados. | Backend |
| [04-ia](04-ia) | Estratégia de estruturação, métricas de qualidade e custos de operação. | IA |
| [05-processo](05-processo) | Fluxo Git, Definition of Done, padrões de código, ambiente e equipe. | Gerência |
| [06-entregas](06-entregas) | Checklist de cada entrega parcial. | Gerência |

## Por onde começar

1. [Escopo do MVP](00-produto/escopo-mvp.md) — o que está dentro e, principalmente, **o que está fora**.
2. [Requisitos funcionais](01-requisitos/requisitos-funcionais.md) e [não funcionais](01-requisitos/requisitos-nao-funcionais.md).
3. [Visão da arquitetura](02-arquitetura/visao-geral.md) e as [decisões](02-arquitetura/decisoes).
4. [Fluxo de trabalho](05-processo/fluxo-git.md) antes do primeiro commit.

## Convenções

- Todo requisito tem um **ID estável** (`RF01`, `RNF03`). O ID viaja do documento ao card, à branch,
  ao commit e ao PR — é isso que garante a rastreabilidade exigida por RNF16.
- Documentos em português; código e identificadores em inglês (ver [glossário](01-requisitos/glossario.md)).
- Decisão de arquitetura que muda o rumo do projeto vira **ADR** — não fica só na conversa.
