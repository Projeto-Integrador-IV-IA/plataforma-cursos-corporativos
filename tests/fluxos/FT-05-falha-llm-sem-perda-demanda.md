# FT-05: Caso de Teste — Falha do LLM sem Perda da Demanda (RNF25)

## Contexto
Validação da regra de preservação de dados (RNF05, RNF09, RF18.1) sob a condição mais crítica: a falha ou indisponibilidade do provedor de LLM durante o processo de estruturação. O teste assegura que a demanda bruta é preservada intacta, que o operador recebe uma mensagem de erro acionável e que o reprocessamento posterior ocorre com sucesso.

---

## Passo a Passo e Resultados Esperados

### 1. Simulação de Falha do Provedor de LLM
* **Ação:** O operador submete uma demanda para estruturação por IA (`POST /api/v1/demands/{id}/structure`), enquanto o serviço de LLM externo está simulando uma falha (timeout, erro HTTP 503 ou mock de exceção de provedor).
* **Resultado Esperado:** 
  * A requisição de estruturação falha devido ao erro simulado no provedor de IA.
  * O sistema captura a exceção adequadamente sem quebrar o fluxo geral da aplicação.

### 2. Verificação da Preservação da Demanda Bruta
* **Ação:** O operador consulta imediatamente o estado da demanda e suas fontes brutas (`GET /api/v1/demands/{id}`).
* **Resultado Esperado:**
  * Confirma-se que **nenhum dado da demanda bruta foi perdido**. Os textos, arquivos e metadados originais permanecem salvos e intactos no banco de dados, cumprindo rigorosamente os requisitos RNF05 e RNF09.

### 3. Notificação de Erro Acionável ao Operador
* **Ação:** O operador verifica a interface ou a resposta da API após a falha.
* **Resultado Esperado:**
  * O erro é relatado ao operador de forma clara e acionável (ex: mensagem indicando instabilidade temporária no serviço de IA, orientando a nova tentativa sem perda de dados).

### 4. Reprocessamento Posterior com Sucesso
* **Ação:** Após o restablecimento do provedor de LLM, o operador aciona novamente a tentativa de estruturação para a mesma demanda.
* **Entrada:** `POST /api/v1/demands/{id}/structure`
* **Resultado Esperado:**
  * O pipeline processa a demanda bruta preservada utilizando o LLM com sucesso, gerando o artefato estruturado correspondente sem a necessidade de redigitar ou reenviar os dados originais.

---

## Critérios de Aceite Atendidos
- [x] Passos, dados de entrada e resultado esperado descritos e executáveis manualmente.
- [x] Preservação integral da demanda bruta verificada após a falha do LLM.
- [x] Tratamento de erro acionável e reprocessamento posterior confirmados.
