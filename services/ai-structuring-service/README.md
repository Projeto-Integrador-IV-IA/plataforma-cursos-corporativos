# ai-structuring-service

Estruturacao do curso por LLM: extracao de requisitos, geracao de ementa e metricas de qualidade.

- **Porta:** `8003`
- **Requisitos atendidos:** RF11, RF12, RNF03, RNF04, RNF05, RNF06
- **Contrato de API:** [`packages/contracts/openapi/ai-structuring-service.yaml`](../../packages/contracts/openapi/ai-structuring-service.yaml)

## Estrutura

```
app/
├── main.py        Ponto de entrada da aplicacao (FastAPI)
├── core/          Configuracao, logging e excecoes
├── api/v1/        Rotas HTTP versionadas (RNF02)
├── schemas/       DTOs de entrada e saida (Pydantic)
├── providers/     Provedores de LLM - unico pacote que fala com SDK de fornecedor
└── services/      Casos de uso / regras de aplicacao
```

## Executar

```bash
# Exporte no shell as variaveis de .env.example e preencha os campos vazios.
pip install -e ".[dev]"
uvicorn app.main:app --reload --port "$AI_STRUCTURING_PORT"
```

> Estado: **scaffolding**. As rotas e o caso de uso ainda nao possuem implementacao - `app/main.py`
> continua stub, entao o servico ainda nao sobe. Ja implementados: configuracao
> (`core/config.py`), contrato de provedor (`providers/base.py`), excecoes (`core/exceptions.py`)
> e os provedores `mock` e `http` com selecao por ambiente.

## Provedor de LLM (RNF03)

O servico conversa com um **contrato**, nao com um fornecedor. `providers/base.py` define
`LLMProvider.complete(prompt, params)`, que devolve o texto bruto do modelo mais os metadados de
execucao (provedor, modelo, tokens, latencia) ou levanta uma excecao tipada de
`core/exceptions.py`: `LLMUnavailableError`, `LLMTimeoutError`, `LLMRateLimitError` ou
`LLMInvalidResponseError`.

Regra que sustenta a [ADR-0006](../../docs/02-arquitetura/decisoes/ADR-0006-saida-da-ia-com-schema-fixo.md):
**nenhum modulo fora de `app/providers/` importa SDK de fornecedor nem cliente HTTP**. Trocar de
provedor e mudar `LLM_PROVIDER`, nao refatorar o servico. A regra e verificada em
[`tests/unit/test_provider_isolation.py`](tests/unit/test_provider_isolation.py).

### Provedores registrados

Quem consome pede `get_llm_provider()` e recebe a implementacao indicada pelo ambiente:

| `LLM_PROVIDER` | Implementacao | Exige | Uso |
|---|---|---|---|
| `mock` (padrao) | `MockLLMProvider` | nada | desenvolvimento, CI e demonstracao sem custo (RNF12) |
| `http` | `HttpLLMProvider` | `LLM_BASE_URL`, `LLM_API_KEY` | fornecedor com API de chat completions compativel com OpenAI |

```bash
# Sem nenhuma chave configurada - resposta fixa, sem rede:
LLM_PROVIDER=mock

# Fornecedor real - endpoint, modelo e chave apenas no ambiente (RNF11):
LLM_PROVIDER=http
LLM_BASE_URL=https://api.exemplo/v1
LLM_COMPLETIONS_PATH=/chat/completions   # opcional; este e o padrao
LLM_MODEL=nome-do-modelo
LLM_API_KEY=...
```

Nome nao registrado em `LLM_PROVIDER` falha na criacao do provedor, listando os disponiveis - erro
de configuracao aparece na subida, nao no meio de uma demanda.

## Testes

```bash
pytest
```
