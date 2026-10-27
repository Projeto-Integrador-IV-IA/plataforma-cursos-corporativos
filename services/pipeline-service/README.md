# pipeline-service

Nucleo do CRM: clientes, demandas, etapas do pipeline, historico e artefatos versionados.

- **Porta:** `8001`
- **Requisitos atendidos:** RF01-RF08, RF13, RF15, RNF07, RNF08, RNF09
- **Contrato de API:** [`packages/contracts/openapi/pipeline-service.yaml`](../../packages/contracts/openapi/pipeline-service.yaml)

## Ordem de recebimento das fontes (RF10, #32)

`POST /api/v1/demands/{id}/raw-inputs` atribui `received_order`, uma sequencia
positiva e unica por demanda. `GET /api/v1/demands/{id}` devolve `raw_inputs`
nessa ordem e expoe a posicao de cada fonte. UUID e data nao determinam a ordem.
No PostgreSQL, a criacao bloqueia a linha da demanda com `FOR UPDATE` ate o commit;
captacoes da mesma demanda sao serializadas antes de calcular a proxima posicao.
A ordem e a de persistencia do original, independente do termino da normalizacao.

`original_content` conserva o texto recebido, inclusive espacos, quebras de linha
e Unicode. A rota de normalizacao aceita somente `normalized_content`; repetir a
normalizacao nao altera a posicao nem o original. O ingestion confirma o original
em uma transacao antes de sanitizar e persistir a copia.

Aplique `alembic upgrade head` antes de iniciar a nova versao. A migration
`20261025_1200` numera fontes existentes por `created_at, id` dentro de cada demanda,
sem alterar os conteudos. Em empates anteriores a essa migration, a chegada real
nao pode ser recuperada; o UUID fornece apenas um desempate deterministico.
O downgrade remove somente a sequencia.

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

> Criacao, consulta e edicao de contexto de demandas implementadas. As demais rotas, incluindo o
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
e o teste `test_versioned_contract_declares_every_published_operation` compara o arquivo
com o `openapi.json` gerado, impedindo que os dois divirjam.

## Consultar e editar o contexto (RF02)

`GET /api/v1/demands/{id}` devolve a demanda com o cliente, a etapa corrente e
os artefatos vinculados, incluindo as versoes necessárias para exibir a estrutura
gerada. `PATCH /api/v1/demands/{id}` aceita `title`, `description` e `owner_id`;
somente os campos enviados sao alterados. Enviar `null` limpa `description` ou
`owner_id`, enquanto etapa, situacao, cliente, artefatos e datas anteriores sao
preservados. Identificadores inexistentes retornam `DEMAND_NOT_FOUND` com HTTP 404.

## Persistir e consultar trechos das fontes (issue #151)

`POST /api/v1/raw-inputs/{id}/segments` recebe os UUIDs estaveis, a posicao e o
conteudo gerados pelo `ingestion-service`. Reenviar o mesmo lote nao duplica
linhas; reutilizar um UUID ou uma posicao com outro conteudo retorna conflito.

`GET /api/v1/raw-inputs/{id}/segments` recupera os trechos de uma fonte pela
ordem original. `GET /api/v1/demands/{id}/segments` reune os trechos de todas as
fontes da demanda. A FK `source_segments.raw_input_id` usa `ON DELETE RESTRICT`,
portanto um trecho orfao nao pode ser criado nem deixado para tras.

## Persistir resultados da IA (RF16.1 consolidado)

`POST /api/v1/demands/{id}/artifacts` grava, na mesma transacao, a resposta
bruta do LLM, o JSON estruturado validado, os metadados da execucao e os
vinculos com todas as fontes utilizadas. Se qualquer parte falhar, artefato,
versao e vinculos sao revertidos. `GET /api/v1/demands/{id}/artifacts` recupera
o agregado completo a partir da demanda.

O campo legado `artifacts.raw_input_id` continua apontando para a primeira
fonte por compatibilidade. A tabela `artifact_sources` representa todas as
fontes e impede, por chave estrangeira composta, vinculos entre demandas
diferentes.

## Consulta interna de credenciais (RF26 consolidado)

O gateway consulta `GET /api/v1/internal/auth/users/by-email` para autenticar o
usuario sem acessar diretamente o banco. A rota exige `X-Service-Key`, cujo
valor vem de `AUTH_SERVICE_KEY` nos dois servicos, e deve permanecer acessivel
somente na rede interna. Ela devolve o hash bcrypt armazenado; senha em texto
puro nao faz parte do modelo nem da resposta.

## Testes

```bash
pytest
```

Os testes de criacao usam SQLite temporario com a cadeia Alembic aplicada e FKs
habilitadas; nao criam registros no banco do projeto.
