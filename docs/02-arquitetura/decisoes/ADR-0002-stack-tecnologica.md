# ADR-0002 — Stack tecnológica

- **Status:** Aceita
- **Data:** 2026-08-19
- **Requisitos:** RNF03, RNF08, RNF12, RNF15

## Contexto

O escopo do MVP não fixa stack ("stack específica a definir conforme ambiente de desenvolvimento").
As restrições que decidem são: equipe do curso de **IA/CD**, prazo de ~15 semanas, operação em
**camada gratuita/estudantil** (RNF12) e necessidade de **banco relacional** com integridade
referencial (RNF08).

## Decisão

| Camada | Escolha |
|---|---|
| Backend | **Python 3.12 + FastAPI** |
| Banco | **PostgreSQL 16** + SQLAlchemy 2 + Alembic |
| Frontend | **React 18 + TypeScript + Vite** |
| IA | API de LLM acessada por camada de provedor abstrata |
| Ambiente local | Docker Compose |
| Qualidade | Ruff (Python), ESLint + Prettier (TypeScript), pytest, Vitest |

## Justificativa

**Python + FastAPI**

- É a linguagem que a equipe de IA/CD já domina — o custo de aprendizado vai para o problema, não
  para a ferramenta.
- Pydantic dá validação de schema de primeira classe, que é exatamente o mecanismo exigido por RNF03
  (saída da IA em formato previsível). O mesmo modelo serve de schema de validação, de documentação
  OpenAPI e de contrato (RNF02).
- OpenAPI é gerado automaticamente, reduzindo o risco de contrato e implementação divergirem.

**PostgreSQL**

- RNF08 exige integridade referencial entre cliente, demanda, etapa e artefato — chave estrangeira
  de verdade, não convenção de aplicação.
- Camada gratuita disponível em vários provedores, o que atende RNF12 sem amarrar a um deles (RNF15).
- Alembic dá migrations versionadas, coerentes com a exigência de auditoria (RNF09).

**React + TypeScript**

- Ecossistema conhecido pelos dois integrantes de frontend; build estático hospedável em camada
  gratuita.
- `strict` do TypeScript alinha os tipos do frontend aos contratos de API (RNF02) e pega divergência
  em tempo de compilação.

## Alternativas consideradas

| Alternativa | Por que não |
|---|---|
| **Django + DRF** | Admin pronto e ORM maduro seriam úteis, mas o framework é pesado para serviços pequenos e o suporte a async é menos direto — relevante para as chamadas ao LLM (RNF06). |
| **Node.js/NestJS no backend** | Unificaria a linguagem com o frontend, mas afasta a equipe de IA do backend de IA. O ecossistema de dados/IA em Python pesa mais aqui. |
| **SQLite** | Custo zero e simplicidade, mas concorrência limitada e migração para produção previsível. RNF15 pede implantação como serviço web padrão. |
| **MongoDB** | O domínio é essencialmente relacional (cliente → demanda → etapa → artefato). RNF08 pede integridade referencial; abrir mão dela criaria trabalho, não economizaria. |
| **Next.js** | Renderização no servidor não traz ganho para uma aplicação interna atrás de login; adiciona complexidade de deploy. |

## Consequências

**Positivas**

- Um único ecossistema de linguagem no backend, incluindo a camada de IA.
- Validação, documentação e contrato saem do mesmo modelo Pydantic.
- Tudo roda em camada gratuita e em container padrão (RNF12, RNF15).

**Negativas**

- Duas linguagens no projeto (Python e TypeScript): o time precisa manter dois conjuntos de
  ferramentas de lint, teste e build. Mitigado pelos alvos unificados no `Makefile`.
- Tipos do frontend precisam acompanhar os contratos manualmente até que se gere código a partir do
  OpenAPI. Item de atenção na revisão de PR que toca `packages/contracts`.
