# ingestion-service

Captura da demanda bruta heterogenea, normalizacao e preparo para a camada de IA. Atende **RNF25** (Documento Consolidado de Requisitos v1.0).

- **Porta:** `8002`
- **Requisitos atendidos:** RF09, RF10, RNF05, RNF25
- **Contrato de API:** [`packages/contracts/openapi/ingestion-service.yaml`](../../packages/contracts/openapi/ingestion-service.yaml)

---

## 1. Responsabilidade e Fronteira

O **Ingestion Service** é o microsserviço de entrada (*gateway de captação*) do pipeline de dados. 
- **O que ele faz:** Recebe requisições de captação de texto bruto multicanal, valida o contrato, aplica validações de conteúdo mínimo (rejeição de textos vazios) e persiste o dado bruto imutável (`original_content`) vinculado à demanda (`demand_id`), além de derivar a cópia normalizada (`normalized_content`).
- **O que ele NÃO faz:** Não executa a estruturação semântica final (responsabilidade da camada de IA) e não realiza chamadas externas de LLM.

---

## 2. Estrutura

```
app/
├── main.py        Ponto de entrada da aplicacao (FastAPI)
├── core/          Configuracao, logging e excecoes
├── api/v1/        Rotas HTTP versionadas (RNF02)
├── schemas/       DTOs de entrada e saida (Pydantic)
└── services/      Casos de uso / regras de aplicacao
```

---

## 3. Endpoints Expostos

O serviço expõe sua API REST documentada via OpenAPI/Swagger:

| Método | Endpoint | Descrição | Parâmetros / Headers |
|---|---|---|---|
| `POST` | `/api/v1/ingestion` | Registra e normaliza uma nova fonte de captação bruta | **Header:** `X-User-ID` (UUID obrigatório do operador)<br>**Body:** `json` (`demand_id`, `source_type` opcional, `text`) |
| `GET` | `/api/v1/ingestion/{id}` | Retorna os detalhes de um registro bruto específico | **Path:** `id` (UUID do registro) |
| `GET` | `/api/v1/ingestion` | Lista os registros brutos cadastrados | **Query Params:** Filtros opcionais |

---

## 4. Variáveis de Ambiente

O serviço utiliza um arquivo `.env` na raiz do microsserviço. Copie o `.env.example` e preencha os campos:

| Variável | Descrição | Padrão / Exemplo |
|---|---|---|
| `DATABASE_URL` | String de conexão com o PostgreSQL | `postgresql://<user>:<password>@localhost:5432/db_name` |
| `INGESTION_PORT` | Porta em que o serviço Uvicorn irá escutar | `8002` |
| `SOURCE_TEXT_MAX_LENGTH` | Limite total da fonte original em caracteres (inteiro >= 10) | `50000` |

---

## 5. Como Executar

```bash
# Exporte no shell as variaveis de .env.example e preencha os campos vazios.
pip install -e ".[dev]"
uvicorn app.main:app --reload --port "$INGESTION_PORT"
```

## 6. Segmentacao citavel da fonte (issue #150)

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

## 7. Proveniencia da fonte (RF10, card #31)

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

## 8. Captacao de audio (RF30, card #164)

`POST /api/v1/ingestion/audio` recebe `multipart/form-data` com os campos
`file` (arquivo) e `demand_id` (UUID), mais o cabecalho obrigatorio `X-User-ID`
(operador). `X-Request-ID` e propagado ao pipeline e aos erros.

Formatos aceitos: **WAV PCM, MP3, M4A, OGG Vorbis/Opus e FLAC**. A extensao e
o MIME sao confrontados com o formato identificado no conteudo. O MIME
generico `application/octet-stream` e aceito apenas quando a inspecao confirma
o formato. A duracao vem dos metadados do arquivo, lidos pelo Mutagen; nao e
um valor informado pelo operador. Isso valida o container e os metadados,
sem transcrever ou executar uma decodificacao completa de todos os formatos.
WAV PCM tambem e verificado contra truncamento dos frames declarados.

| Variavel | Padrao | Unidade e regra |
|---|---|---|
| `AUDIO_MAX_BYTES` | `25000000` | Bytes do arquivo, ate 25 MB decimais; inteiro positivo |
| `AUDIO_MAX_DURATION_SECONDS` | `3600` | Segundos, ate 60 minutos; numero positivo e finito |

Os valores iniciais seguem os limites propostos na documentacao de STT
(card #175 / PR #291). Limitam armazenamento, duracao e custo potencial antes
da integracao do provedor; devem ser revistos apos medicao da PoC.
O limite e inclusivo. Arquivo maior retorna **413 / AUDIO_TOO_LARGE**, com
o maximo em bytes; duracao maior retorna **422 / AUDIO_TOO_LONG**, com o maximo
em segundos. Formato invalido retorna **422 / AUDIO_INVALID_FORMAT**.

Exporte as variaveis no processo ou use o `.env` da raiz com Docker Compose.
O Compose encaminha os mesmos limites a ingestao e pipeline. Recrie os
containers apos alterar a configuracao; no uso isolado, configure ambos e
reinicie os processos. O arquivo e lido ate o teto mais um byte para detectar
excesso sem carregar o restante na validacao. O parser multipart pode usar
arquivo temporario durante o recebimento; ele nao e o armazenamento duravel.

O pipeline grava o binario integral e SHA-256 em `audio_inputs`, ligado a
`raw_inputs`, na mesma transacao. A fonte registra `AUDIO`, demanda, operador,
data e ordem de recebimento. O commit ocorre antes do HTTP 201 e nenhuma
chamada STT ocorre durante a captacao. A resposta traz `raw_input_id`,
`audio` (metadados), `status=RECEBIDA` e `transcription_status=PENDENTE`.
Esse estado informa que o arquivo foi captado: nao representa um job ja
disparado. A integracao ElevenLabs e o reprocessamento pertencem aos cards
#165 e #166. Esta entrega nao efetua chamadas pagas.

Para recuperar o original, consulte no pipeline
`GET /api/v1/raw-inputs/{raw_input_id}/audio`. O endpoint devolve os bytes,
o MIME e `X-Content-SHA256`; os metadados aparecem tambem na consulta da fonte
e no detalhe da demanda. Nao se grava nome de arquivo como se fosse texto:
em fontes `AUDIO`, `original_content` fica vazio e `normalized_content` nulo
ate o trabalho de transcricao. O endpoint de texto recusa `source_type=AUDIO`
e orienta usar o upload.

```sh
curl -X POST http://localhost:8002/api/v1/ingestion/audio \
  -H "X-User-ID: <UUID-do-operador>" \
  -F "demand_id=<UUID-da-demanda>" \
  -F "file=@reuniao.wav;type=audio/wav"
```

Testes: `python -m pytest tests/integration/test_audio_ingestion.py`.

## 9. Transcrição de Áudio e Integração STT (RF30, planejamento)

Esta captacao (secao 8) apenas recebe e preserva o audio; nenhuma chamada STT
ocorre nela. A transcricao propriamente dita e a integracao do provedor
pertencem aos cards #165 e #166. Estimativas de custo e configuracao de
exemplo para essa etapa futura:

- **Formatos Aceitos:** `.mp3`, `.wav`, `.m4a`, `.ogg`, `.flac`.
- **Limites de Arquivo:** Tamanho máximo de 25 MB por arquivo e duração máxima de 60 minutos por arquivo de áudio enviado.
- **Configuração de Variáveis (`.env`):**
  ```env
  STT_PROVIDER=openai
  OPENAI_API_KEY=sua-chave-aqui
  STT_MAX_AUDIO_MB=25
  ```

Limites de Consumo e Cota (RF30 / RNF22): O serviço aplica validações de cota para preservar a camada gratuita estudantil, limitando o processamento base a 2 horas de áudio por tenant/mês (dentro do teto global de 10h mensais do MVP).

## 10. Testes

```bash
pytest
```

## 11. Limite configuravel da fonte (RNF13 consolidado, card #42)

`SOURCE_TEXT_MAX_LENGTH` limita o campo `text` de `POST /api/v1/ingestion`
antes da persistencia e da normalizacao. O padrao e **50.000 caracteres**:
preserva o teto ja adotado no RF12 (#35) e acompanha o limite atual do contrato
de estruturacao por IA. E um ponto de partida ajustavel apos as medicoes da
PoC, sem garantia de equivalencia com tokens ou com a janela de todo modelo.

A contagem inclui espacos, quebras de linha e caracteres Unicode, usando
`len(text)`; nao mede bytes nem tokens. O minimo do RF12 continua sendo
10 caracteres nao brancos. Valores de configuracao menores que 10, fracionarios
ou nao numericos sao invalidos.

Para reduzir o teto, exporte `SOURCE_TEXT_MAX_LENGTH=20000` no processo do
servico ou defina esse valor no `.env` da raiz usado pelo Docker Compose.
O arquivo `.env` isolado do servico e somente um template para exportacao.
Reinicie o servico (ou recrie o container) depois de alterar a configuracao,
pois ela e armazenada em cache por processo. O Compose encaminha a variavel
ao container e o `/openapi.json` publica o `maxLength` efetivo da instancia.
O contrato YAML versionado descreve o ambiente com o valor padrao.

Uma fonte acima do teto retorna HTTP **422**, `VALIDATION_ERROR`, com
`error.details.issues` indicando `body.text`, tipo `source_text_too_long` e
mensagem `A fonte deve conter no maximo 20000 caracteres.` (no exemplo).
O texto e recusado integralmente: nao e truncado, persistido nem normalizado.
O cabecalho `X-Request-ID`, quando enviado, e preservado no envelope de erro.

Aumentar esse limite permite captar fontes maiores, mas nao altera o teto
independente de 50.000 caracteres da estruturacao por IA. Para processa-las
nessa etapa e necessario ajustar o contrato correspondente ou segmentar a
entrada em trabalho separado.
