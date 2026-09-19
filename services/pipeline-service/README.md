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
# Exporte no shell as variaveis de .env.example e preencha os campos vazios.
pip install -e ".[dev]"
uvicorn app.main:app --reload --port "$PIPELINE_PORT"
```

> Criacao de demandas implementada. As demais rotas de negocio, incluindo o
> cadastro de clientes (dependencia RF01.1), ainda sao scaffolding nesta branch.

## Criar demanda (RF02)

Com as variaveis de ambiente configuradas, aplique o schema antes de iniciar:

```bash
alembic upgrade head
```

O Swagger fica em `http://localhost:8001/docs` quando o servico estiver em execucao.
`POST /api/v1/demands` aceita, por exemplo:

```json
{
  "client_id": "00000000-0000-0000-0000-000000000002",
  "title": "Treinamento de lideranca",
  "description": "Capacitacao de vinte gestores.",
  "owner_id": "00000000-0000-0000-0000-000000000001"
}
```

Substitua os IDs por registros existentes no banco. `client_id` e `title` sao
obrigatorios; contexto (`description`) e responsavel (`owner_id`) sao opcionais.
A demanda e persistida como `ABERTA`, na etapa `CAPTACAO`. Situacao e etapa nao
podem ser escolhidas no cadastro; pertencem ao fluxo de gestao do pipeline.

- `201`: demanda persistida, incluindo UUID, vinculo ao cliente e datas.
- `404`: cliente ou responsavel inexistente, no envelope `error` da plataforma.
- `409`: referencia removida entre validacao e escrita, com rollback.
- `422`: campo obrigatorio ausente, UUID invalido, titulo vazio ou campo extra,
  no envelope `error` da plataforma.

A migration inicial ja inclui os campos e `client_id NOT NULL`, com FK e
`ON DELETE RESTRICT`. A revisao `20260916_1200` acrescenta a restricao de titulo
preenchido. Se houver titulos vazios antigos, corrija-os antes do upgrade; a
migration nao altera silenciosamente registros historicos.

Rastreabilidade: a integridade referencial que sustenta esta rota e o **RNF08**
da [matriz versionada](../../docs/01-requisitos/matriz-rastreabilidade.md). O
Documento Consolidado de Requisitos v1.0 numera esse mesmo requisito como RNF14;
o ID valido aqui e sempre o da matriz.

A operacao fica no contrato do servico,
[`pipeline-service.yaml`](../../packages/contracts/openapi/pipeline-service.yaml),
e o teste `test_versioned_contract_matches_published_creation` compara o arquivo
com o `openapi.json` gerado, impedindo que os dois divirjam.

## Testes

```bash
pytest
```

Os testes de criacao usam SQLite temporario com a cadeia Alembic aplicada e FKs
habilitadas; nao criam registros no banco do projeto.
