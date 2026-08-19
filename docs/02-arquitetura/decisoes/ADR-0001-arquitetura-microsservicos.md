# ADR-0001 — Arquitetura em microsserviços

- **Status:** Aceita
- **Data:** 2026-08-19
- **Requisitos:** RNF01, RNF13

## Contexto

RNF01 exige explicitamente microsserviços independentes comunicando-se por API, nomeando quatro
frentes: ingestão/normalização, estruturação (IA), pipeline/persistência e frontend web.

Além da exigência, há duas razões de projeto:

1. **Equipe de 6 em frentes paralelas** (backend 2, IA 1, frontend 2, gerência/documentação).
   Fronteiras claras reduzem conflito de merge e permitem avanço simultâneo.
2. **Roadmap pós-MVP conhecido.** Custeio, busca de instrutores e integrações externas (RF-F1 a
   RF-F5) precisam entrar depois **sem reescrever o núcleo** (RNF13).

## Decisão

Quatro serviços de backend, com fronteiras traçadas pelo **motivo de mudança** de cada um:

| Serviço | Muda quando… |
|---|---|
| `pipeline-service` | O modelo de negócio muda (nova etapa, novo tipo de artefato). |
| `ingestion-service` | Surge uma nova forma de entrada de demanda. |
| `ai-structuring-service` | O prompt, o modelo ou o provedor de LLM mudam. |
| `gateway-service` | A política de acesso ou a topologia de rotas muda. |

O `gateway-service` é um acréscimo à lista literal de RNF01. Justificativa: RF16 e RNF10 exigem
autenticação e controle de acesso, e concentrar isso em um ponto é mais seguro e mais barato do que
replicar validação de token nos três serviços de domínio (ver [ADR-0005](ADR-0005-gateway-como-fronteira-de-autenticacao.md)).

## Alternativas consideradas

| Alternativa | Por que não |
|---|---|
| **Monólito modular** | Mais simples de operar e provavelmente suficiente para o volume real (2–3 propostas/dia). Descartada porque RNF01 exige microsserviços e porque a divisão facilita o trabalho paralelo de 6 pessoas. |
| **Um serviço por entidade** (cliente, demanda, artefato…) | Fragmentação sem ganho: as três entidades mudam juntas e compartilham integridade referencial (RNF08). Transação distribuída seria criada sem necessidade. |
| **Estruturação por IA dentro do pipeline** | Acopla o núcleo do CRM ao provedor de LLM. Trocar de modelo passaria a mexer no serviço que guarda os dados. |

## Consequências

**Positivas**

- Frentes trabalham em paralelo com baixo acoplamento.
- Trocar provedor de LLM não toca o CRM.
- Evoluções futuras entram como serviço novo, consumindo o pipeline por API (RNF13).
- A falha do LLM fica isolada e não derruba o CRM.

**Negativas — assumidas conscientemente**

- Mais peças para subir e depurar do que um monólito resolveria. Mitigado por Docker Compose e por
  log correlacionado por `X-Request-ID`.
- Latência adicional de rede entre serviços. Relevante para RNF07 (≤ 500 ms) — por isso o gateway
  encaminha as rotas de CRM diretamente ao pipeline, sem agregação intermediária.
- Consistência entre serviços é eventual em caso de falha parcial. Mitigado pela ordem obrigatória
  do fluxo: persistir o bruto **primeiro** (RNF05).
