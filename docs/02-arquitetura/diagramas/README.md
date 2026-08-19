# Diagramas

Diagramas ficam **no repositório, como texto** (Mermaid), não como imagem colada. Assim entram em
revisão de PR, versionam junto com o código e não ficam desatualizados sem que ninguém perceba.
O GitHub renderiza Mermaid nativamente.

## Diagramas existentes

| Diagrama | Onde |
|---|---|
| Contexto do sistema | [visao-geral.md](../visao-geral.md#contexto) |
| Serviços e dependências | [visao-geral.md](../visao-geral.md#serviços) |
| Fluxo end-to-end da estruturação | [visao-geral.md](../visao-geral.md#fluxo-end-to-end-da-estruturação) |
| Fluxo do MVP | [escopo-mvp.md](../../00-produto/escopo-mvp.md#fluxo-do-mvp) |
| Modelo entidade-relacionamento | [modelo-dados.md](../../03-dados/modelo-dados.md) |
| Máquina de estados do pipeline | [modelo-dados.md](../../03-dados/modelo-dados.md#máquina-de-estados-do-pipeline) |
| Cronograma (Gantt) | [cronograma.md](../../00-produto/cronograma.md) |

## Pendentes para a 2ª parcial (15/09)

- [ ] Diagrama de casos de uso do operador
- [ ] Diagrama de sequência do retrocesso de etapa (RF06)
- [ ] Diagrama de implantação, quando o ambiente de homologação for definido ([Q5](../../01-requisitos/questoes-em-aberto.md))

## Convenção

- Rótulos em português; nomes de serviço como aparecem no repositório.
- Um diagrama responde **uma** pergunta. Diagrama que tenta mostrar tudo não mostra nada.
- Se precisar de imagem exportada para o relatório impresso, gere a partir do Mermaid — a fonte
  continua sendo o texto versionado.
