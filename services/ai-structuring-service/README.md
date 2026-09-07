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

> Estado: **scaffolding**. Os modulos ainda nao possuem implementacao, salvo a
> configuracao (`core/config.py`), o contrato de provedor (`providers/base.py`) e as
> excecoes (`core/exceptions.py`).

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

## Testes

```bash
pytest
```
