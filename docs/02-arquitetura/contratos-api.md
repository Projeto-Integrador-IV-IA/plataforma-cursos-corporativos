# Contratos de API

Atende **RNF02**: contratos de API versionados e documentados entre os serviços.

A especificação executável vive em [`packages/contracts/openapi/`](../../packages/contracts/openapi).
Este documento explica as **regras** que ela precisa seguir.

## Regra de processo

**Contrato antes de código.** Toda mudança de API começa por um PR em `packages/contracts`, revisado
por representantes de backend, IA e frontend. Só depois vem a implementação. Isso evita a situação
clássica de frontend e backend implementarem interpretações diferentes da mesma rota.

## Versionamento

Todo caminho é prefixado por `/api/v1`.

| Tipo de mudança | Exemplo | Como proceder |
|---|---|---|
| **Compatível** | Campo opcional novo na resposta; endpoint novo | Evolui a v1 |
| **Incompatível** | Campo removido ou renomeado; tipo alterado; campo que vira obrigatório; valor novo em enum consumido por `switch` | Abre a v2; a v1 continua no ar até todos migrarem |

Os enums do domínio (etapas do pipeline, status da demanda, tipos de artefato) **são contrato**.
Mudar um valor é mudança incompatível.

## Convenções

- **Recursos no plural, em inglês:** `/clients`, `/demands`, `/artifacts`.
- **Subrecursos aninhados quando há posse:** `/demands/{id}/transitions`.
- **Identificadores:** UUID em toda a plataforma. Nada de id sequencial exposto.
- **Datas:** ISO 8601 com fuso (`2026-09-15T14:30:00-03:00`).
- **Paginação:** `?page=1&size=20`; a resposta traz `items`, `total`, `page`, `size`.
- **Filtros de listagem** (RF03): `?status=`, `?client_id=`, `?from=`, `?to=`.
- **Corpo em `snake_case`**, coerente com Python; o frontend converte na borda, se precisar.

## Códigos de resposta

| Código | Quando |
|---|---|
| `200` | Leitura ou atualização bem-sucedida |
| `201` | Recurso criado — traz `Location` |
| `400` / `422` | Entrada inválida |
| `401` | Sem autenticação (RF16) |
| `403` | Autenticado, sem permissão (RNF10) |
| `404` | Recurso inexistente |
| `409` | Conflito de estado — ex.: transição de etapa inválida (RF05) |
| `502` / `504` | Serviço a jusante falhou ou expirou — inclui o LLM (RNF05) |

## Formato de erro

Único em toda a plataforma, conforme
[`error.schema.json`](../../packages/contracts/schemas/error.schema.json):

```json
{
  "error": {
    "code": "INVALID_STAGE_TRANSITION",
    "message": "Não é possível avançar de captação para proposta.",
    "details": { "from": "CAPTACAO", "to": "PROPOSTA" },
    "request_id": "0f3c..."
  }
}
```

`code` é estável e legível por máquina; `message` é em português e exibível ao operador. A mensagem
**nunca** revela detalhe interno de infraestrutura (RNF10).

## Cabeçalhos

| Cabeçalho | Uso |
|---|---|
| `Authorization: Bearer <token>` | Toda rota, exceto `login` e `health` (RF16) |
| `X-Request-ID` | Correlação do fluxo entre serviços; gerado no gateway se ausente (RNF09) |

## Superfícies por serviço

| Serviço | Prefixos | Requisitos |
|---|---|---|
| `gateway-service` | `/api/v1/auth/*` e o encaminhamento de todos os demais | RF16, RF17, RNF10 |
| `pipeline-service` | `/api/v1/clients`, `/api/v1/demands`, `/api/v1/artifacts` | RF01–RF08, RF13, RF15 |
| `ingestion-service` | `/api/v1/ingestion` | RF09, RF10, RF17 |
| `ai-structuring-service` | `/api/v1/structuring` | RF11, RF12, RNF03, RNF04 |

Todos expõem `/health` e `/ready`, sem autenticação.

## Timeouts

Timeout é parte do contrato, não detalhe de implementação:

| Chamada | Alvo | Requisito |
|---|---|---|
| CRUD do CRM | ≤ 500 ms | RNF07 |
| Estruturação por IA | ≤ 15 s | RNF06 |

Estouro de timeout na estruturação é **falha recuperável**: a demanda bruta permanece registrada
(RNF05).

> **Estado.** Os caminhos ainda não estão declarados nos arquivos OpenAPI — isso é entrega da Fase 2
> (até 15/09), antes do início da implementação.
