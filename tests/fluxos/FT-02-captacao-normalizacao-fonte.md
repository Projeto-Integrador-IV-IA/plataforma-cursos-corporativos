# FT-02: Caso de Teste de Fluxo — Captação e Normalização de Fonte

**Mapeamento de Requisitos:** RF09, RF10, RNF05, RNF25  
**Escopo:** `ingestion-service` (:8002), `pipeline-service` (:8001)  
**Status de Execução:** Executado com Sucesso (Evidência em PR)

---

## 1. Objetivo e Regra de Ouro

Verificar que o conteúdo original fornecido pelo operador/cliente é persistido de forma **intacta (byte a byte)** no banco de dados **antes** de qualquer tentativa de processamento ou normalização, garantindo a imutabilidade exigida por RNF05.

---

## 2. Cenário 1: Caminho Feliz — Ingestão de Três Fontes Reais e Distintas

### Passo 1.1: Ingerir E-mail com Cabeçalho e Assinatura
- **Ação:** `POST /api/v1/ingestion` (via `ingestion-service`)
- **Dados de Entrada (Payload JSON):**
  ```json
  {
    "demand_id": "<UUID_DE_UMA_DEMANDA_EXISTENTE>",
    "source": "EMAIL",
    "content": "---------- Forwarded message ---------\nFrom: cliente@empresa.com\nDate: Seg, 12 de Out de 2026 at 10:00\nSubject: Proposta de Treinamento\n\nOla, precisamos de um curso de Python para nossa equipe.\nAtenciosamente,\nCarlos Silva\nGerente de TI"
  }

Resultado Esperado (API): Status 201 Created

Validação de Integridade no Banco (pipeline-service DB):

O campo original_content na tabela raw_inputs deve conter exatamente a string enviada (incluindo quebras de linha \n, cabeçalhos encaminhados e assinatura), sem nenhuma alteração.

O campo normalized_content pode conter a versão limpa (ou nula se a normalização estrutural dependente do card #34 ainda estiver em andamento).

### Passo 1.2: Ingerir Transcrição de Reunião
Ação: POST /api/v1/ingestion

Dados de Entrada:

{
  "demand_id": "<UUID_DE_UMA_DEMANDA_EXISTENTE>",
  "source": "TRANSCRICAO",
  "content": " Joao: Vamos fechar a ementa focando em microsservicos.\n Maria: Concordo, precisamos incluir Docker e FastAPI."
}

Resultado Esperado (API): Status 201 Created

Validação: original_content preservado integralmente com as marcações de tempo e nomes.

### Passo 1.3: Ingerir Conversa de WhatsApp
Ação: POST /api/v1/ingestion

Dados de Entrada:

{
  "demand_id": "<UUID_DE_UMA_DEMANDA_EXISTENTE>",
  "source": "MENSAGENS",
  "content": "[14/10/2026 14:32] Cliente: Ola bom dia\n[14/10/2026 14:33] Cliente: O curso tera certificado?"
}

Resultado Esperado (API): Status 201 Created

Validação: original_content preservado byte a byte.

## 3. Cenário 2: Caminhos de Erro (Validações de Limite)
### Passo 2.1: Fonte Abaixo do Conteúdo Mínimo / Vazia
Ação: POST /api/v1/ingestion com content: ""

Resultado Esperado: Status 400 Bad Request ou 422 Unprocessable Entity

Motivo: O sistema rejeita textos vazios para evitar poluição da base.

### Passo 2.2: Fonte Acima do Limite Máximo de Tamanho
Ação: POST /api/v1/ingestion com uma string gigantesca (> limite de caracteres permitido no payload).

Resultado Esperado: Status 413 Payload Too Large ou erro de validação de tamanho máximo.

4. Nota sobre o Formato Interno Comum (Card #34)
O passo de verificação da padronização completa para o formato interno unificado (ai-structuring-service) encontra-se Pendente, aguardando a finalização da entrega do card #34 (Padronização das entradas para o formato interno comum).

Atualmente, garante-se a preservação do texto original bruto (original_content) e a sanitização básica opcional em normalized_content.

5. Registro de Execução
Data de Execução: 09/10/2026

Ambiente: Docker Compose Local (ingestion-service, pipeline-service, Postgres)

Resultado: Testes executados com sucesso via requisições HTTP simuladas. O conteúdo original sobreviveu intacto em todas as três fontes.