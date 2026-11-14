# FT-04: Caso de Teste — Aprovação Bloqueada Sem Revisão (RNF25)

## Contexto
Validação da regra de negócio crítica da plataforma: **a IA nunca é a palavra final**. O sistema deve impedir obrigatoriamente a aprovação de qualquer artefato estruturado pela IA enquanto o operador humano não registrar a revisão e validação do conteúdo.

---

## Passo a Passo e Resultados Esperados

### 1. Tentativa de Aprovação Direta (Sem Revisão)
* **Ação:** O operador tenta aprovar o artefato gerado pela IA imediatamente após o término da estruturação, pulando a etapa de revisão humana.
* **Entrada:** `POST /api/v1/demands/{id}/approve` (ou transição para o status `APROVADO` sem flag de revisão).
* **Resultado Esperado:** 
  * A operação é **bloqueada** pelo sistema.
  * A API retorna um código de erro adequado (ex: `422 Unprocessable Entity` ou `409 Conflict`) informando claramente o motivo do bloqueio (ex: `"Aprovação negada: é obrigatório registrar a revisão humana antes de aprovar o artefato"`).

### 2. Registro da Revisão Humana
* **Ação:** O operador realiza a leitura e edição necessária do artefato na interface e submete formalmente o registro de revisão.
* **Entrada:** `POST /api/v1/demands/{id}/review` ou submissão do formulário de revisão validado.
* **Resultado Esperado:**
  * O sistema registra com sucesso a revisão, vinculando o ID do revisor humano e o timestamp da validação.

### 3. Sucesso na Aprovação Após Revisão
* **Ação:** Após a revisão devidamente registrada, o operador repete a tentativa de aprovação do artefato.
* **Entrada:** `POST /api/v1/demands/{id}/approve`
* **Resultado Esperado:**
  * A operação é processada e aceita com sucesso, permitindo o avanço do artefato para o status de aprovado.

### 4. Auditoria da Decisão na Trilha
* **Ação:** O operador consulta a linha do tempo ou o histórico de auditoria da demanda (`GET /api/v1/demands/{id}/timeline`).
* **Resultado Esperado:**
  * A trilha exibe de forma clara e imutável a tentativa bloqueada anterior, o evento de registro da revisão humana e, por fim, o evento de aprovação definitiva com os respectivos responsáveis.

---

## Critérios de Aceite Atendidos
- [x] Passos, dados de entrada e resultado esperado descritos e executáveis manualmente.
- [x] Bloqueio rigoroso verificado quando a revisão não foi registrada.
- [x] Auditabilidade da decisão e do fluxo garantida na trilha da demanda.
