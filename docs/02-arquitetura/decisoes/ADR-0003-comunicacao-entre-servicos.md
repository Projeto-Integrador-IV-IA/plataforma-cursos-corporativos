# ADR-0003 — Comunicação síncrona por HTTP/REST

- **Status:** Aceita
- **Data:** 2026-08-19
- **Requisitos:** RNF01, RNF02, RNF05, RNF06

## Contexto

Os serviços precisam conversar. A estruturação por IA é a operação mais lenta do sistema (alvo de
≤ 15 s por demanda, RNF06) e a mais sujeita a falha, por depender de API externa (RNF05).

A tentação natural é introduzir fila de mensagens. A pergunta é se ela resolve um problema **que
existe hoje**.

## Decisão

**HTTP/REST síncrono, JSON, contratos em OpenAPI 3.1**, para toda a comunicação entre serviços no MVP.

- Cada serviço expõe `/api/v1/...`; o prefixo de versão é obrigatório (RNF02).
- Erros seguem um formato único em toda a plataforma (`error.schema.json`).
- `X-Request-ID` é propagado em toda chamada, permitindo reconstruir o fluxo de uma demanda no log
  entre serviços (RNF09).
- Timeouts são explícitos e distintos por tipo de operação: CRM segue RNF07, estruturação segue RNF06.

A pasta `packages/contracts/events/` fica **reservada** para contratos assíncronos, caso a evolução
pós-MVP exija.

## Alternativas consideradas

| Alternativa | Por que não |
|---|---|
| **Fila de mensagens (RabbitMQ, Redis, Celery)** | Resolveria a lentidão do LLM de forma elegante, mas acrescenta um componente para operar, monitorar e hospedar — contra RNF12 (camada gratuita) — para um volume real de 2–3 propostas por dia. Complexidade sem problema correspondente. |
| **gRPC** | Mais eficiente, porém pior de depurar, sem suporte nativo no navegador e com ferramental que a equipe não domina. O ganho de latência é irrelevante no volume esperado. |
| **GraphQL no gateway** | Boa resposta para múltiplos clientes com necessidades distintas de dados. Há um cliente só. |

## Consequências

**Positivas**

- Depurável com `curl` e com a interface do navegador; qualquer integrante inspeciona uma chamada.
- Documentação automática via OpenAPI, coerente com RNF02.
- Nenhuma infraestrutura adicional para hospedar (RNF12).

**Negativas**

- A requisição de estruturação fica aberta enquanto o LLM responde. Mitigado por: timeout explícito,
  estado de processamento visível ao operador (RF17) e persistência prévia do bruto (RNF05).
- Se a estruturação passar a exceder consistentemente o alvo de RNF06, esta decisão precisa ser
  reavaliada — a fila volta à mesa e este ADR é substituído.
