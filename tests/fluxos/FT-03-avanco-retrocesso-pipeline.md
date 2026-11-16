# FT-03: Caso de Teste — Avanço e Retrocesso no Pipeline (RNF25)

## Contexto
Validação da integridade do fluxo de gestão de demandas. O teste assegura que o operador pode avançar e retroceder uma demanda entre as etapas do pipeline sem perda de dados, garantindo que os artefatos e versões anteriores sobrevivam ao retrocesso e que transições não permitidas sejam bloqueadas.

---

## Passo a Passo e Resultados Esperados

### 1. Avanço de Etapa no Pipeline
* **Ação:** O operador avança uma demanda da etapa inicial (ex: `CAPTACAO`) para a próxima etapa (ex: `ESTRUTURACAO`).
* **Entrada:** `POST /api/v1/demands/{id}/transition` com o payload indicando a etapa destino válida.
* **Resultado Esperado:** 
  * A demanda atualiza sua etapa com sucesso.
  * A linha do tempo (`GET /api/v1/demands/{id}/timeline`) registra o evento de avanço com o carimbo de data/hora e o operador responsável.

### 2. Retrocesso de Etapa e Verificação da Trilha
* **Ação:** O operador decide retornar a demanda da etapa atual para uma etapa anterior (ex: retornar de `REVISAO` para `ESTRUTURACAO`).
* **Entrada:** `POST /api/v1/demands/{id}/transition` (ou rota específica de retrocesso).
* **Resultado Esperado:**
  * O sistema permite o retrocesso a qualquer etapa anterior válida.
  * A trilha completa exibe o histórico completo de idas e vindas de forma imutável e transparente.

### 3. Verificação de Integridade de Artefatos e Versões
* **Ação:** O operador consulta os artefatos vinculados à demanda após o ciclo de avanço e retrocesso (`GET /api/v1/demands/{id}/artifacts`).
* **Resultado Esperado:**
  * Confirma-se que **nenhum artefato, dado bruto ou versão gerada foi perdido ou apagado** durante o retrocesso. As versões anteriores permanecem intactas e acessíveis para auditoria.

### 4. Caminho de Erro: Transição Não Permitida
* **Ação:** O operador tenta realizar um salto de etapa inválido ou pular etapas obrigatórias do fluxo (ex: saltar diretamente de `CAPTACAO` para a conclusão final).
* **Entrada:** `POST /api/v1/demands/{id}/transition` com transição fora da regra de negócio.
* **Resultado Esperado:**
  * A API rejeita a operação retornando o código de erro adequado (ex: `422 Unprocessable Entity` ou `409 Conflict`) acompanhado do envelope de erro padrão da plataforma.

---

## Critérios de Aceite Atendidos
- [x] Passos, dados de entrada e resultado esperado descritos e executáveis manualmente.
- [x] Integridade da trilha e preservação de artefatos/versões verificadas após ida e volta.
- [x] Caminho de erro para transições inválidas devidamente coberto.

