# ingestion-service

Captura da demanda bruta heterogenea, normalizacao e preparo para a camada de IA.

- **Porta:** `8002`
- **Requisitos atendidos:** RF09, RF10, RNF05
- **Contrato de API:** [`packages/contracts/openapi/ingestion-service.yaml`](../../packages/contracts/openapi/ingestion-service.yaml)

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
uvicorn app.main:app --reload --port "$INGESTION_PORT"
```

## Segmentacao citavel da fonte (issue #150)

A unidade de segmentacao e a **linha logica nao vazia depois da sanitizacao**.
Essa regra trata cada mensagem ou turno exportado como uma unidade e mantem
linhas independentes de e-mails, transcricoes e anotacoes na ordem em que foram
recebidas. Linhas em branco apenas separam visualmente o texto e nao geram
trechos vazios.

`segment_text` devolve cada trecho com a posicao iniciada em 1 e um UUIDv5
deterministico. O identificador deriva do `raw_input_id`, da posicao e do texto
sanitizado do trecho. Assim, reprocessar a mesma fonte gera os mesmos IDs;
fontes diferentes com o mesmo texto continuam tendo identificadores distintos.

O endpoint de captacao preserva o texto original no `pipeline-service` antes de
qualquer processamento. Depois da confirmacao, uma copia e sanitizada em
`normalizers/text_normalizer.py` e gravada separadamente em `normalized_content`.
Cabecalhos e assinaturas de e-mail, metadados de WhatsApp, HTML, Markdown,
caracteres invisiveis e espacamento redundante sao removidos sem resumir ou
reescrever o conteudo semantico.

## Proveniencia da fonte (RF10, card #31)

`POST /api/v1/ingestion` aceita `source_type` opcional. Quando omitido ou nulo,
`normalizers/source_detector.py` identifica marcas explicitas de e-mail,
mensagens exportadas, transcricao ou anotacao. Sem marcas suficientes, usa
`OUTRO`. Um `source_type` informado pelo operador sempre prevalece, inclusive
`OUTRO`; valores desconhecidos ou vazios continuam sendo rejeitados com 422.
A inferencia examina o texto original antes da normalizacao, sem modifica-lo.

Exemplo com inferencia:

```json
{
  "demand_id": "<UUID da demanda>",
  "text": "De: marina@example.com\nAssunto: Treinamento\n\nPrecisamos de 20 vagas."
}
```

Enviar o cabecalho `X-User-ID` com o UUID do operador. A resposta confirma o
`source_type` efetivamente gravado e o `raw_input_id`. Para substituir a
sugestao na captacao, informar por exemplo `"source_type": "ANOTACAO"`.

O `pipeline-service` expoe `GET /api/v1/raw-inputs/{raw_input_id}` com `source`
(canal/tipo de origem), `author_id` (operador que recebeu a fonte), `created_at`
(data de recebimento registrada pelo banco), `demand_id`, `original_content`
e `normalized_content`. Esses metadados tambem estao na fonte do detalhe da
demanda; o texto normalizado e consultavel na rota individual da fonte.
O remetente citado no texto nao e confundido com o operador identificado pelo
cabecalho `X-User-ID`. Nao ha novo campo nem migration: a proveniencia reutiliza as colunas
introduzidas no RF09. A ordenacao de recebimento pertence ao card #32.

## Testes

```bash
pytest
```
