# pipeline-service

Nucleo do CRM: clientes, demandas, etapas do pipeline, historico e artefatos versionados.

- **Porta:** `8001`
- **Requisitos atendidos:** RF01-RF08, RF13, RF15, RNF07, RNF08, RNF09
- **Contrato de API:** [`packages/contracts/openapi/pipeline-service.yaml`](../../packages/contracts/openapi/pipeline-service.yaml)

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
cp ../../.env.example ../../.env
pip install -e ".[dev]"
uvicorn app.main:app --reload --port 8001
```

> Estado: **scaffolding**. Os modulos ainda nao possuem implementacao.

## Testes

```bash
pytest
```
