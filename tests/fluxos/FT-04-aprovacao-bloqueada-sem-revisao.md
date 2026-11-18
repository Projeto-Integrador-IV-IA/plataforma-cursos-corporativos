# FT-04: Caso de Teste — Decisão de Revisão Sobre Versão Desatualizada (RF19.2)

## Contexto
Validação da regra de negócio crítica da plataforma: **a IA nunca é a palavra final**. O sistema
registra formalmente a decisão humana (aprovar, rejeitar ou devolver) sobre a versão vigente de um
artefato, e recusa a decisão quando a versão informada já deixou de ser a vigente — a decisão nunca
pode valer, em silêncio, para um conteúdo que já foi substituído.

> **Nota de reconciliação (17/11/2026):** esta versão substitui um desenho anterior deste caso de
> teste, que previa dois passos separados (`POST /demands/{id}/review` e, só depois,
> `POST /demands/{id}/approve` bloqueado sem o primeiro). O que foi implementado e testado contra a
> API real é um único endpoint por artefato, com três desfechos possíveis — mais simples e com o
> mesmo efeito prático: nenhum artefato é aprovado sem que uma pessoa registre a decisão, e a
> decisão é sempre sobre uma versão específica, nunca sobre "o artefato em geral".

---

## Passo a Passo e Resultados Esperados

### 1. Decisão Sobre a Versão Vigente
* **Ação:** O operador lê a estrutura gerada pela IA (tela de revisão) e registra a decisão.
* **Entrada:** `POST /api/v1/artifacts/{artifact_id}/review` com `{version_number, decision, reason}`,
  `decision` em `APROVADO` | `REJEITADO` | `DEVOLVIDO`, autor lido do cabeçalho `X-User-ID`.
* **Resultado Esperado:**
  * `201 Created`, com o registro contendo `id`, `version_number`, `decision`, `author_id`,
    `created_at` e `reason`.
  * `REJEITADO` e `DEVOLVIDO` **exigem** `reason` não vazia — sem ela, `422` antes de qualquer
    gravação (`ArtifactReviewCreate`, validado no cliente e no servidor).
  * `APROVADO` **não exige** `reason`.

### 2. Decisão Sobre Versão Que Já Não É a Vigente — Bloqueio
* **Ação:** Entre a tela de revisão abrir e o clique na decisão, outra pessoa salva uma edição
  (RF19.1), criando uma versão nova. O operador decide sobre a versão que já leu, agora desatualizada.
* **Entrada:** `POST /api/v1/artifacts/{artifact_id}/review` com `version_number` da versão antiga.
* **Resultado Esperado:**
  * **Bloqueado**: `409 Conflict`, código `ARTIFACT_VERSION_STALE`, mensagem orientando a recarregar
    a versão vigente antes de decidir. Nenhum registro de revisão é criado.
  * A interface trata este código especificamente — não como falha genérica — e pede para recarregar.

### 3. Histórico e Última Decisão
* **Ação:** O operador consulta o histórico de decisões do artefato.
* **Entrada:** `GET /api/v1/artifacts/{artifact_id}/reviews`.
* **Resultado Esperado:**
  * Lista todas as decisões já registradas, da mais antiga à mais recente — append-only, nenhuma é
    alterada ou removida (mesma garantia de gatilho no banco das demais trilhas do serviço).
  * `GET /api/v1/demands/{demand_id}/artifacts` (e a tela de revisão) expõe a mesma informação
    resumida em `latest_review`, sem chamada extra.

---

## Critérios de Aceite Atendidos
- [x] Passos, dados de entrada e resultado esperado descritos e executáveis contra a API real.
- [x] Decisão sem justificativa (`REJEITADO`/`DEVOLVIDO`) recusada antes de qualquer gravação.
- [x] Decisão sobre versão desatualizada bloqueada (409), sem criar registro.
- [x] Histórico append-only e auditável, com autor, data e justificativa de cada decisão.
- [x] Verificado tanto em teste automatizado
  ([`test_artifact_review.py`](../../services/pipeline-service/tests/integration/test_artifact_review.py),
  `DemandStructuringView.test.tsx`) quanto ao vivo contra a stack real.
