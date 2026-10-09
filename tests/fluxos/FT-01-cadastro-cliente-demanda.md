# FT-01: Caso de Teste de Fluxo — Cadastro de Cliente e Demanda

**Mapeamento de Requisitos:** RF01, RF02, RNF08, RNF25  
**Escopo:** `pipeline-service` (:8001), `gateway-service` (:8000), `web` (:5173)  
**Status de Execução:** Executado com Sucesso (Evidência em PR)

---

## 1. Padrão de Formato do Teste de Fluxo

Este documento estabelece o modelo padrão para os testes de fluxo do sistema (`FT-01` a `FT-06`). Cada passo deve conter obrigatoriamente:
- **Ação / Endpoint:** Ação na interface ou chamada HTTP efetuada.
- **Dados de Entrada Concretos:** Valores exatos enviados na requisição.
- **Resultado Esperado (UI / API):** Código HTTP, JSON retornado e comportamento visual.
- **Validação no Banco de Dados:** Estado do registro gravado no PostgreSQL no `pipeline-service`.

---

## 2. Cenário 1: Caminho Feliz (Happy Path)

### Passo 1.1: Criar Cliente Valido
- **Ação:** `POST /api/v1/clients` (via Gateway :8000)
- **Dados de Entrada:**
  ```json
  {
    "name": "Academia de Cursos Tech LTDA",
    "cnpj": "12.345.678/0001-95",
    "segment": "Educacao Executiva",
    "contact_name": "Mariana Souza",
    "contact_email": "mariana@academiatech.com.br",
    "contact_phone": "(45) 99988-7766",
    "notes": "Cliente focado em treinamento corporativo."
  }

### Resultado Esperado (API): Status 201 Created

 - Retorna id (UUID formatado).

 - Retorna active: true e created_at em timestamp UTC.

 - Validação DB (pipeline-service DB):

SELECT id, name, cnpj, active FROM clients WHERE cnpj = '12.345.678/0001-95';
-- Retorna 1 linha com name = 'Academia de Cursos Tech LTDA' e active = true

### Passo 1.2: Conferir Cliente na Listagem e Detalhe
- Ação: GET /api/v1/clients?search=Academia e GET /api/v1/clients/{client_id}

- Resultado Esperado: Status 200 OK

- Objeto do cliente retornado com todos os campos idênticos aos cadastrados.

### Passo 1.3: Criar Demanda Vinculada ao Cliente
- Ação: POST /api/v1/demands

- Dados de Entrada:
{
  "client_id": "<UUID_CRIADO_NO_PASSO_1.1>",
  "title": "Treinamento em Gestao de Obras e Estruturas",
  "description": "Curso presencial para engenheiros com foco em BIM e execucao."
}

### Resultado Esperado (API): Status 201 Created

- current_stage deve ser inicializado estritamente como "CAPTACAO".

- status deve ser inicializado como "ABERTA".

### Validação DB (pipeline-service DB):

SELECT id, client_id, current_stage, status FROM demands WHERE title LIKE 'Treinamento em Gestao%';
-- Exige client_id do cliente criado e current_stage = 'CAPTACAO'

### 3. Cenário 2: Caminhos de Erro (Validacoes e Excecoes)
# Passo 2.1: Campo Obrigatório Ausente no Cliente
- Ação: POST /api/v1/clients

- Dados de Entrada: {"segment": "Educacao"} (Sem name)

- Resultado Esperado: Status 422 Unprocessable Entity

- Mensagem de erro informando que o campo name é obrigatório.

# Passo 2.2: CNPJ Mal Formatado ou Invalido
- Ação: POST /api/v1/clients

- Dados de Entrada: {"name": "Empresa X", "cnpj": "123.456"}

- Resultado Esperado: Status 400 Bad Request ou 422 Unprocessable Entity

- Erro de validação de formato de CNPJ.

# Passo 2.3: CNPJ Duplicado (Conflito 409)
- Ação: Tentar cadastrar um segundo cliente com o mesmo CNPJ "12.345.678/0001-95".

- Resultado Esperado: Status 409 Conflict

- Retorno de erro indicando violação da restrição de unicidade do CNPJ.

# Passo 2.4: Criar Demanda para Cliente Inexistente
- Ação: POST /api/v1/demands com client_id: "00000000-0000-0000-0000-000000000000"

- Resultado Esperado: Status 404 Not Found ou 400 Bad Request

- Violação de Integridade Referencial (RNF08). A demanda órfã é rejeitada.

### 4. Cenário 3: Inativação do Cliente (Pendente / Parcial)
- Status: Aguardando entrega total do card #25 (Inativar/Reativar cliente).

- Passo Planejado: PATCH /api/v1/clients/{client_id}/inactivate

- Comportamento Esperado: Altera active = false. As demandas ativas associadas mantêm o registro histórico sem exclusão em cascata.

### 5. Registro de Execução (Evidência)
- Data da Execução: 08/10/2026

- Ambiente: Docker Compose Local (pipeline-service, PostgreSQL 16)

- Resultado: 100% dos testes do fluxo executados e aprovados.

---

