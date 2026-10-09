# Instruções e Contexto do Projeto (CLAUDE.md)

## Visão Geral
Plataforma de capacitação corporativa baseada em inteligência artificial para gestão de demandas, transcrição, estruturação de conteúdos e acompanhamento de pipeline.

## Regras de Escopo do MVP
- **Integrações Externas / STT (Speech-to-Text):** A integração de STT foi aprovada pelo orientador e migrada do escopo pós-MVP (Bloco B) para dentro do **MVP**, permitindo a transcrição automatizada de áudios e reuniões para compor as fontes brutas das demandas.
- **Microsserviços do MVP:**
  - `gateway-service`: Borda, autenticação e rotas (RF16).
  - `pipeline-service`: CRM, pipeline e artefatos (RF01–RF08, RF13, RF15).
  - `ingestion-service`: Captação multicanal de fontes brutas (RF09).
  - `ai-structuring-service`: Processamento e estruturação por IA.

## Comandos Úteis
- **Testes:** `pytest`
- **Validação de Linters:** `ruff check`, `ruff format --check`
- **Validação de Contratos:** `openapi-spec-validator`