# Equipe e responsabilidades

Equipe de 6 integrantes, organizada em cinco frentes. Preencha os nomes e os usuários do GitHub —
os mesmos usuários devem constar em [`.github/CODEOWNERS`](../../.github/CODEOWNERS).

| Frente | Integrante | GitHub | Responsabilidade principal |
|---|---|---|---|
| Gerência | | | Cronograma, board, contato com o cliente, entregas parciais, custos |
| Documentação | | | Requisitos, relatório técnico, artigos, revisão documental |
| Backend 1 | | | `pipeline-service`, modelo de dados, migrations |
| Backend 2 | | | `ingestion-service`, `gateway-service`, integração |
| IA | | | `ai-structuring-service`, prompts, métricas de qualidade |
| Frontend 1 | | | `web` — cadastros e listagens |
| Frontend 2 | | | `web` — pipeline, revisão da saída da IA |

> São 7 linhas para 6 pessoas: uma pessoa acumula duas frentes, conforme combinado na equipe.
> Ajuste a tabela para a distribuição real.

## Áreas de propriedade

Cada frente é dona de uma parte do repositório e **revisa obrigatoriamente** os PRs que a tocam:

| Área | Dono |
|---|---|
| `services/pipeline-service`, `infra/db` | Backend |
| `services/ingestion-service`, `services/gateway-service` | Backend |
| `services/ai-structuring-service`, `docs/04-ia` | IA |
| `web` | Frontend |
| `packages/contracts` | Backend + IA + Frontend (revisão dupla) |
| `docs`, `.github` | Documentação + Gerência |

## Responsabilidades transversais

**Gerência**

- Mantém o board atualizado e o cronograma visível
- É o **único** canal de contato com o cliente — evita informação conflitante
- Aprova qualquer item que amplie o escopo do MVP
- Consolida e submete as entregas parciais

**Documentação**

- Mantém requisitos e matriz de rastreabilidade coerentes com o que foi implementado
- Revisa os documentos antes de cada entrega
- Conduz o relatório técnico e os artigos

**Todos**

- Revisar PR é trabalho, não favor: meta de resposta no mesmo dia útil
- Card sem ID de requisito não entra na sprint
- Impedimento se comunica no dia em que aparece, não na revisão da sprint

## Rituais

| Ritual | Frequência | Duração |
|---|---|---|
| Planejamento da sprint | Semanal | 30 min |
| Acompanhamento | Meio da sprint | 15 min |
| Revisão + retrospectiva | Fim da sprint | 45 min |
| Alinhamento com o cliente | Conforme necessidade | Conduzido pela gerência |

## Datas que valem para todos

| Data | Evento |
|---|---|
| 25/08 | 1ª parcial |
| 15/09 | 2ª parcial |
| 22/09 | Pré-banca |
| 20/10 | 3ª parcial |
| 17/11 | 4ª parcial — MVP funcional |
| 24/11 | Banca |
