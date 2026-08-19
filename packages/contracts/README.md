# Contratos de API

Fonte única dos contratos entre os microsserviços (RNF02). Um serviço só sabe do outro o que está
declarado aqui.

## Regra de ouro

**Contrato antes de código.** Mudança de API começa por um PR neste pacote, revisado por representantes
de backend, IA e frontend (ver [`CODEOWNERS`](../../.github/CODEOWNERS)). Só depois vem a implementação.

## Estrutura

```
openapi/    Especificação OpenAPI 3.1 de cada serviço
schemas/    JSON Schemas compartilhados (a saída da IA é o mais crítico — RNF03)
events/     Reservado para contratos de eventos assíncronos (evolução futura)
```

## Versionamento

- Todo caminho é prefixado por `/api/v1`.
- **Mudança compatível** (campo opcional novo, endpoint novo): evolui a v1.
- **Mudança incompatível** (campo removido/renomeado, tipo alterado, obrigatoriedade nova): abre a v2.
  A v1 permanece no ar até que todos os consumidores migrem.
- Enums do domínio (etapas do pipeline, status, tipos de artefato) são contrato: mudar valor é mudança
  incompatível.

## Schemas críticos

| Schema | Por quê |
|---|---|
| `structured-course.schema.json` | Formato de saída da IA. RNF03 exige saída consistente e previsível; é contra este schema que a resposta do LLM é validada e é sobre ele que as métricas de RNF04 são calculadas. |
| `error.schema.json` | Formato único de erro em toda a plataforma, para o frontend tratar qualquer serviço da mesma forma. |

> Estado: **esqueleto**. Os caminhos e schemas são preenchidos na Fase 2 (modelagem e arquitetura,
> até 15/09), antes do início da implementação.
