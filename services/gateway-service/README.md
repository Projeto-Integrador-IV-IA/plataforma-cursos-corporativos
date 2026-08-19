# gateway-service

Porta de entrada unica da plataforma: autenticacao, roteamento e agregacao para o frontend.

- **Porta:** `8000`
- **Requisitos atendidos:** RF16, RF17, RNF10, RNF02
- **Contrato de API:** [`packages/contracts/openapi/gateway-service.yaml`](../../packages/contracts/openapi/gateway-service.yaml)

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
uvicorn app.main:app --reload --port 8000
```

> Estado: **scaffolding**. Os modulos ainda nao possuem implementacao.

## Testes

```bash
pytest
```
