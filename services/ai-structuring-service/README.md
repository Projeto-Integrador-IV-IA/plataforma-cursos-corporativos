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

> Estado: **scaffolding**. As rotas de negocio ainda nao possuem implementacao. Ja implementados:
> configuracao (`core/config.py`), contrato de provedor (`providers/base.py`), excecoes
> (`core/exceptions.py`), os provedores `mock` e `http` com selecao por ambiente, a chamada
> resiliente ao provedor (`services/structuring_service.py`) e a traducao das falhas em resposta
> HTTP (`main.py`).

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

## Falha e timeout do LLM (RNF05)

O provedor pode falhar; a demanda bruta, nao. Quem persiste o texto colado e o `ingestion-service`,
**antes** de qualquer chamada ao modelo - este servico nao abre transacao nem escreve no banco de
outro microsservico, entao falhar aqui nao tem como desfazer o registro do bruto.

O que cabe a este servico esta em [`services/structuring_service.py`](app/services/structuring_service.py):

| Camada | Responsabilidade |
|---|---|
| `providers/` | Uma chamada e uma tentativa. Traduz timeout, erro de rede e status HTTP na excecao tipada correspondente, que informa em `retryable` se repetir tem chance. |
| `services/structuring_service.py` | Politica de retentativa (`tenacity`, ate `LLM_MAX_RETRIES` repeticoes, backoff exponencial ou `Retry-After`) e desfecho: `StructuringOutcome` carrega a demanda intacta, as tentativas gastas, o tempo decorrido e o erro tipado. |
| `main.py` | Traduz a excecao de dominio no corpo unico de erro da plataforma (RNF02), com o status da propria falha e o `X-Request-ID` da requisicao. |

`structure()` nao deixa excecao de provedor escapar: o chamador recebe sempre um desfecho, com a
demanda bruta em maos para reprocessar. O corpo de erro identifica a causa (`LLM_TIMEOUT`,
`LLM_UNAVAILABLE`, `LLM_RATE_LIMITED`, `LLM_INVALID_RESPONSE`), qual demanda falhou, quantas
tentativas houve e se vale repetir - sem expor credencial (RNF11) nem dado do cliente (RNF10).

Cobertura em [`tests/unit/test_structuring_service.py`](tests/unit/test_structuring_service.py) e
[`tests/unit/test_error_responses.py`](tests/unit/test_error_responses.py).

## Testes

```bash
pytest
```
