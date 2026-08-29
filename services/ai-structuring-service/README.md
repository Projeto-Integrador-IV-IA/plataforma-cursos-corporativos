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
└── services/      Casos de uso / regras de aplicacao
```

## Executar

```bash
# Exporte no shell as variaveis de .env.example e preencha os campos vazios.
pip install -e ".[dev]"
uvicorn app.main:app --reload --port "$AI_STRUCTURING_PORT"
```

> Estado: **scaffolding**. Os modulos ainda nao possuem implementacao.

## Testes

```bash
pytest
```
