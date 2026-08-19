# Guia de Contribuição

Fluxo obrigatório do projeto (RNF14): **Card → Branch → Commits → Pull Request → Review → Merge**.
Nada entra na `main` sem passar por PR revisado.

---

## 1. Card

Todo trabalho começa por um card no **GitHub Projects**. O título do card deve conter o **ID do
requisito** que ele atende — é isso que preserva a rastreabilidade requisito → card → sprint (RNF16).

```
[RF05] Avançar e retroceder etapas do pipeline
[RNF03] Definir schema de saída da estruturação por IA
```

Cards são agrupados por microsserviço (label `svc:pipeline`, `svc:ingestion`, `svc:ai`, `svc:gateway`, `svc:web`).

## 2. Branch

Uma branch por card, criada a partir da `main` atualizada:

```
<tipo>/<ID-requisito>-<descricao-curta>
```

| Tipo | Uso |
|---|---|
| `feat` | Nova funcionalidade |
| `fix` | Correção de defeito |
| `docs` | Documentação |
| `refactor` | Refatoração sem mudança de comportamento |
| `test` | Apenas testes |
| `chore` | Infra, dependências, configuração |

Exemplos: `feat/RF05-transicao-etapas`, `docs/RNF04-metricas-qualidade`.

## 3. Commits

Padrão **Conventional Commits**, com o ID do requisito no escopo:

```
feat(RF05): permitir retrocesso livre entre etapas do pipeline
fix(RNF05): preservar demanda bruta quando o LLM excede o timeout
docs(RF14): documentar fluxo de revisão humana da saída da IA
```

Commits pequenos e coesos. Mensagem em português, no imperativo.

## 4. Pull Request

- Abra o PR para a `main` preenchendo o [template](.github/pull_request_template.md).
- Vincule o card (`Closes #123`).
- Marque o requisito atendido e confirme os itens da Definition of Done.
- CI verde é pré-requisito para review.

## 5. Review

- **Mínimo 1 aprovação** de outro integrante; 2 quando o PR toca contrato de API (`packages/contracts`)
  ou modelo de dados.
- O revisor verifica: atende ao requisito? tem teste? respeita o contrato? não vaza segredo?
- Comentários são sugestões até que o autor responda; discussões abertas bloqueiam o merge.

## 6. Merge

- **Squash and merge**, mantendo a mensagem no padrão de commit.
- Branch apagada após o merge.
- Card movido para *Done* no board.

---

## Definition of Done

Ver [docs/05-processo/definition-of-done.md](docs/05-processo/definition-of-done.md). Resumo:

- [ ] Requisito atendido conforme descrito no card
- [ ] Testes cobrindo o caminho feliz e ao menos um erro
- [ ] `make check` passa localmente
- [ ] Contrato de API atualizado em `packages/contracts` (se aplicável, RNF02)
- [ ] Documentação afetada atualizada
- [ ] Matriz de rastreabilidade atualizada
- [ ] Nenhum segredo no código (RNF11)

## Padrões de código

- **Python**: Ruff (lint + format), type hints obrigatórios em funções públicas, docstrings em português.
- **TypeScript**: ESLint + Prettier, `strict` ligado, sem `any`.
- **Nomes**: código e identificadores em inglês; documentação, docstrings e comentários em português.
  O mapeamento domínio ↔ código está no [glossário](docs/01-requisitos/glossario.md).

Detalhes em [docs/05-processo/padroes-codigo.md](docs/05-processo/padroes-codigo.md).

## Segurança

Chaves de API, senhas e tokens **nunca** entram no repositório (RNF11). Use `.env` local, sempre
partindo de `.env.example`. Se um segredo vazar em commit, avise a gerência imediatamente — rotacionar
a chave é obrigatório, remover o commit não basta.
