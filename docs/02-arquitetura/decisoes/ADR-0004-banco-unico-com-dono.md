# ADR-0004 — Banco único com dono exclusivo

- **Status:** Aceita
- **Data:** 2026-08-19
- **Requisitos:** RNF01, RNF08, RNF09, RNF12, RNF13

## Contexto

A ortodoxia de microsserviços recomenda um banco por serviço. Mas o domínio deste projeto é
fortemente relacional: cliente → demanda → etapa → artefato → versão. RNF08 exige **integridade
referencial** entre exatamente essas entidades, e RNF09 exige que nenhuma transição de etapa ou
versão de artefato se perca.

Se cliente e demanda vivessem em bancos diferentes, a chave estrangeira viraria convenção de
aplicação e a atomicidade da transição de etapa (gravar o histórico **e** atualizar a etapa corrente)
exigiria transação distribuída — complexidade real, dentro de um prazo de 15 semanas e de um
orçamento de custo zero (RNF12).

## Decisão

**Um único banco PostgreSQL, de propriedade exclusiva do `pipeline-service`.**

- Nenhum outro serviço tem string de conexão para este banco. `ingestion-service` e
  `ai-structuring-service` acessam os dados **apenas pela API** do pipeline.
- `ai-structuring-service` não tem persistência própria: recebe texto, devolve estrutura.
- `ingestion-service` não tem persistência própria: usa a API do pipeline para gravar o bruto.
- O schema é criado **exclusivamente por migrations do Alembic**, versionadas no repositório. Nada de
  DDL manual em banco — inclusive o `infra/db/init/01-init.sql` se limita a extensões.

A regra que preserva o desacoplamento não é "um banco por serviço", é **"um dono por dado"**.

## Alternativas consideradas

| Alternativa | Por que não |
|---|---|
| **Um banco por serviço** | Correto no papel, mas quebraria a integridade referencial exigida por RNF08 e obrigaria a coordenar transações entre serviços para atender RNF09. Custo alto para um sistema com um único usuário e 2–3 negociações por dia. |
| **Banco compartilhado, acesso direto de todos** | Mais simples no curto prazo e desastroso no médio: qualquer serviço passa a depender do schema interno de outro, e a evolução independente exigida por RNF13 desaparece. |
| **Schemas separados no mesmo banco** | Meio-termo que preserva a chave estrangeira, mas mantém a tentação do acesso direto. Não resolve nada que a fronteira de API não resolva melhor. |

## Consequências

**Positivas**

- Integridade referencial garantida pelo próprio banco (RNF08).
- A transição de etapa grava histórico e estado corrente na **mesma transação** — nunca divergem (RNF09).
- Um único conjunto de migrations para manter, dentro do orçamento de operação (RNF12).
- O desacoplamento continua real, porque o acesso é por API (RNF13).

**Negativas — assumidas conscientemente**

- O `pipeline-service` é o ponto único de falha do sistema: se ele cai, nada funciona. Aceito para o
  MVP; o volume real não justifica alta disponibilidade.
- A regra "só o pipeline conecta no banco" é **social, não técnica**. Precisa ser defendida em code
  review — um `DATABASE_URL` aparecendo no `.env` de outro serviço é motivo para reprovar o PR.
- Se um serviço futuro precisar de dado próprio (ex.: base de custo, RNF-F1), ele traz o **seu**
  banco, sem reabrir esta decisão.
