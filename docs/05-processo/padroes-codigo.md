# Padrões de código

## Idioma

| O quê | Idioma |
|---|---|
| Identificadores (classes, funções, variáveis, tabelas, rotas) | **Inglês** |
| Docstrings, comentários, mensagens de commit, documentação | **Português** |
| Mensagens de erro exibidas ao operador | **Português** |
| Códigos de erro (`code` da API) | **Inglês**, em maiúsculas |

O mapeamento negócio ↔ código está no [glossário](../01-requisitos/glossario.md). Nada de
`demandaService` ou `ClientePipeline` — meio-termo é o pior dos dois mundos.

## Python

Ferramenta única: **Ruff** (lint + format). Configuração em cada `pyproject.toml`.

- Linha de até 100 caracteres.
- Type hints obrigatórios em toda função pública.
- Docstring em toda classe e função pública, explicando **o que** e **por quê** — o *como* está no
  código.
- Import absoluto (`from app.core.config import ...`), nunca relativo.
- Exceção específica, nunca `except Exception: pass`.
- `logger`, nunca `print`.
- f-string, nunca concatenação nem `%`.

**Camadas — a regra que sustenta a arquitetura:**

```
rota  →  service (caso de uso)  →  repository  →  banco
```

Rota não fala com repositório. Repositório não contém regra de negócio. Service não sabe o que é
HTTP. Quebrar isso é o começo do fim da testabilidade.

**Comentário de requisito.** Onde o código existe por causa de um requisito não óbvio, cite o ID:

```python
# Persiste o bruto antes de chamar o LLM: falha do modelo nao pode
# custar o texto que o operador ja colou (RNF05).
```

## TypeScript / React

**ESLint + Prettier.** `strict` ligado no `tsconfig`.

- **Sem `any`.** Se o tipo não é conhecido, é `unknown` com validação.
- Componente funcional com hooks; nada de componente de classe.
- Um componente por arquivo, nomeado igual ao arquivo.
- Chamada de rede só em `src/services` — componente não chama `fetch`.
- Tipos de API em `src/types`, derivados dos [contratos](../../packages/contracts).
- Estado de servidor no cliente de dados; estado local em `useState`. Não misturar.

**Nomes de arquivo:** componentes em `PascalCase.tsx`; o resto em `camelCase.ts`.

## SQL e migrations

- Toda mudança de schema por migration Alembic. **Zero DDL manual.**
- Migration reversível: `downgrade` implementado e testado.
- Nome descritivo: `20260916_1430_add_stage_transitions.py`.
- Tabelas no plural, colunas em `snake_case`.
- Chave estrangeira sempre com `ON DELETE` explícito — o padrão implícito é armadilha.

## Testes

| Tipo | Onde | O que valida |
|---|---|---|
| Unitário | `services/<svc>/tests/unit` | Regra de negócio isolada, sem banco nem rede |
| Integração | `services/<svc>/tests/integration` | Rota + banco, dentro de um serviço |
| End-to-end | `tests/e2e` | Fluxo atravessando serviços |

- Nome do teste descreve o comportamento:
  `test_retrocesso_para_etapa_anterior_registra_transicao`.
- Um teste, uma asserção conceitual.
- Teste que depende de ordem de execução está errado.
- Teste de IA usa `LLM_PROVIDER=mock` — determinístico e sem custo.

## O que não fazer

| Anti-padrão | Por quê |
|---|---|
| Segredo no código | RNF11. Bloqueado pela CI. |
| Outro serviço acessando o banco do pipeline | Quebra [ADR-0004](../02-arquitetura/decisoes/ADR-0004-banco-unico-com-dono.md). |
| `UPDATE` ou `DELETE` em `stage_transitions` / `artifact_versions` | Destrói a trilha de auditoria (RNF09). |
| Implementar item do Bloco B | Desvio de escopo. Passa pela gerência antes. |
| Prompt como string no código | Impede comparar medições (RNF03, RNF04). |
| Mudar contrato sem atualizar `packages/contracts` | Quebra RNF02 e o trabalho de quem consome. |
