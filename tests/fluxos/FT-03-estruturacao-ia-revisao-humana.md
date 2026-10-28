# FT-03: Caso de Teste — Estruturação por IA e Revisão Humana

## Contexto
Validação do diferencial de ponta a ponta da plataforma: o envio de fontes normalizadas, a geração de estrutura por IA (retornando os cinco campos essenciais e lacunas sinalizadas), seguida pela revisão e edição humana que gera uma nova versão do artefato versionado.

---

## Passo a Passo e Resultados Esperados

### 1. Disparo da Estruturação por IA
* **Ação:** O operador aciona a estruturação a partir das fontes normalizadas de uma demanda.
* **Entrada:** `POST /api/v1/demands/{id}/structure` com as fontes da demanda.
* **Resultado Esperado:** 
  * O sistema processa a chamada de forma assíncrona exibindo feedback global de progresso (RF17).
  * O `pipeline-service` grava na mesma transação o resultado bruto do LLM e o JSON estruturado validado (`POST /api/v1/demands/{id}/artifacts`).

### 2. Validação dos Cinco Campos e Lacunas
* **Ação:** O operador consulta o artefato gerado na interface ou via API (`GET /api/v1/demands/{id}/artifacts`).
* **Resultado Esperado:**
  * O JSON retornado contém rigorosamente os **cinco campos obrigatórios** da estrutura pedagógica/corporativa.
  * **Sinalização de lacunas:** Se houver trechos vagos ou informações ausentes nas fontes, as lacunas vêm explicitamente sinalizadas no payload estruturado para atenção do revisor humano.

### 3. Revisão e Edição Humana
* **Ação:** O operador revisa a estrutura na tela dedicada e realiza ajustes/edições manuais nos campos desejados, salvando as alterações.
* **Entrada:** `PATCH` ou submissão de nova versão editada pelo revisor.
* **Resultado Esperado:**
  * A interface permite a edição fluida e transparente (RF14).
  * A gravação dispara a criação de uma **nova versão do artefato** (`GET /api/v1/artefatos/{artifactId}/versoes`), mantendo o histórico imutável das versões anteriores (RF08).

---

## Critérios de Aceite Atendidos
- [x] Passos, dados de entrada e resultado esperado descritos e demonstrados.
- [x] Sinalização de lacuna verificada na estrutura da IA.
- [x] Versionamento da edição gerado corretamente a cada alteração humana.
