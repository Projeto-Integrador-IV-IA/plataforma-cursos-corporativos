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

O endpoint de captacao preserva o texto original no `pipeline-service` antes de
qualquer processamento. Depois da confirmacao, uma copia e sanitizada em
`normalizers/text_normalizer.py` e gravada separadamente em `normalized_content`.
Cabecalhos e assinaturas de e-mail, metadados de WhatsApp, HTML, Markdown,
caracteres invisiveis e espacamento redundante sao removidos sem resumir ou
reescrever o conteudo semantico.

## Testes

```bash
pytest
```
