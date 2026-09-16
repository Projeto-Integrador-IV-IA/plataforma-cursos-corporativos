# Compatibilidade da criacao de demandas com os PRs

Consulta feita em 16/09/2026 pela API do GitHub, incluindo arquivos alterados e
comentarios de revisao. As referencias usadas foram obtidas diretamente dos
heads dos PRs. A base `dev` estava em `5120e03`; a branch RF02 parte dessa base.

## Ajustes aplicados na RF02

- O contrato principal `pipeline-service.yaml` foi preservado exatamente como
  esta na base. A operacao implementada e seus schemas ficam em
  [`pipeline-demands-create.yaml`](../../packages/contracts/openapi/pipeline-demands-create.yaml).
  Isso evita que a RF02 e o PR #146 disputem a substituicao do mesmo esqueleto.
- UUIDs, nomes dos campos, FK obrigatoria e as cinco etapas do modelo ja
  integrado foram mantidos. A demanda nasce `ABERTA`, em `CAPTACAO`, compativel
  com as regras do PR #148.
- A migration inicial nao foi recriada nem reescrita. A nova revisao acrescenta
  apenas a validacao de titulo preenchido e continua a cadeia existente.
- Erros `404`, `409` e `422` usam o envelope `error` da plataforma. A validacao
  HTTP de demandas e encapsulada no proprio router, sem substituir os handlers
  globais que outras tasks poderao implementar.
- O cadastro nao devolve um `Location` para uma rota de consulta inexistente.
  Listagem e detalhe nao fazem parte desta task.

## PRs abertos verificados

| PR | Escopo | Resultado com RF02 |
|---|---|---|
| [#142](https://github.com/Projeto-Integrador-IV-IA/plataforma-cursos-corporativos/pull/142) | Fluxo Git | Merge sem conflito de arquivos |
| [#143](https://github.com/Projeto-Integrador-IV-IA/plataforma-cursos-corporativos/pull/143) | Guia, README e matriz | Merge sem conflito de arquivos |
| [#144](https://github.com/Projeto-Integrador-IV-IA/plataforma-cursos-corporativos/pull/144) | Contrato ingestion | Merge sem conflito de arquivos |
| [#145](https://github.com/Projeto-Integrador-IV-IA/plataforma-cursos-corporativos/pull/145) | Contrato IA e schema de curso | Merge sem conflito de arquivos |
| [#146](https://github.com/Projeto-Integrador-IV-IA/plataforma-cursos-corporativos/pull/146) | Contrato completo pipeline | Merge sem conflito de arquivos; divergencias de contrato abaixo |
| [#147](https://github.com/Projeto-Integrador-IV-IA/plataforma-cursos-corporativos/pull/147) | Contrato gateway e fluxo Git | Merge sem conflito de arquivos |
| [#148](https://github.com/Projeto-Integrador-IV-IA/plataforma-cursos-corporativos/pull/148) | Regras das etapas | Merge sem conflito de arquivos; estado inicial compativel |

A verificacao usou `git merge-tree`, com um indice temporario contendo a RF02.
Os sete merges individuais e a combinacao dos sete PRs ficaram sem conflitos.
Nenhum merge foi aplicado a branch de trabalho; nenhuma branch ou PR remoto foi
alterado. O resultado vale para os heads consultados, nao para futuras edicoes.

## Consolidacao com o PR #146

O contrato proposto no #146 precisa ser alinhado ao modelo integrado nos PRs
[#136](https://github.com/Projeto-Integrador-IV-IA/plataforma-cursos-corporativos/pull/136)
e [#137](https://github.com/Projeto-Integrador-IV-IA/plataforma-cursos-corporativos/pull/137)
e as regras do #148 antes de ser utilizado como contrato da API implementada.
O arquivo isolado da RF02 documenta o comportamento efetivamente testado.

| Ponto | Proposta atual do #146 | Modelo e criacao implementados |
|---|---|---|
| Caminho | `/demands`, sem prefixo nos servers | `/api/v1/demands` |
| Identificadores | Exemplos `cli-9901` e `dem-8f92a10c` | UUIDs, coerentes com as FKs |
| ID da resposta | `demand_id` | `id` |
| Etapa inicial | `triagem` | `CAPTACAO` |
| Etapas | Sete valores em minusculas | `CAPTACAO`, `ESTRUTURACAO`, `PRODUTO`, `PROPOSTA`, `ACOMPANHAMENTO` |
| Situacao e responsavel | Ausentes na resposta de demanda | `status` e `owner_id` |
| Prioridade | Campo `priority` | Nao existe no modelo desta task; entrada recusada |
| Autor | Campo obrigatorio `created_by` | Autor da criacao depende da autenticacao; `owner_id` representa o responsavel |
| Erros do cadastro | `400`, `401`, `500` | `404`, `409`, `422`, com envelope `error`; autenticacao e task separada |

Na consolidacao, usar a operacao e os schemas do contrato RF02 para documentar
o POST real, preservar as demais operacoes do #146 e alinhar os exemplos e enums
compartilhados. Nao traduzir `triagem` para `CAPTACAO` ou inventar prioridade e
autor apenas para fazer os exemplos passarem: isso mudaria o dominio existente.
O merge sem conflitos de arquivos nao comprova compatibilidade dos consumidores
com os exemplos e schemas divergentes do #146.

## Dependencia de clientes

O [PR #133](https://github.com/Projeto-Integrador-IV-IA/plataforma-cursos-corporativos/pull/133)
foi fechado sem merge. Seu head ainda tem um modelo antigo de clientes e uma
migration que cria `clients`, ja incluida no schema relacional integrado.
Importar esse PR inteiro duplicaria a criacao de tabelas e substituiria partes
do modelo atual; por isso ele nao foi incorporado.

A RF02 usa `Client` do modelo integrado e exige um cliente persistido. Quando o
cadastro RF01.1 for retomado, deve reutilizar esse modelo e a fabrica de sessoes
existentes. A revisao do #133 tambem orientou o envelope do `422` e a ausencia de
um `Location` que prometa uma consulta ainda nao implementada.

## Validacao

- RF02 isolada: 43 testes aprovados, incluindo banco temporario migrado,
  persistencia, referencias invalidas, rollback, Swagger e contrato isolado.
- Ruff lint, formatacao e `git diff --check` aprovados.
- Integracao conjunta dos sete PRs: 74 testes do pipeline-service aprovados na
  copia temporaria, incluindo os testes das etapas do PR #148. Esse resultado
  verifica o codigo do servico; nao valida consumidores dos contratos de IA,
  ingestion ou gateway.
- A migration nao foi aplicada ao banco real. Os testes de banco usam SQLite;
  a geracao de SQL offline para PostgreSQL tambem foi validada.

## Heads consultados

| PR | Commit |
|---|---|
| #142 | `e42c102db75853bff2b31c25b9afbf56d11d102d` |
| #143 | `c7c00ac68361cbfcf60bc42c92d58ff09526593b` |
| #144 | `4b24f4108374216807191c79ac611e1538a63fd4` |
| #145 | `67b286eb3542056423c15f1c27a1a12569c2981d` |
| #146 | `1ef094b87b0003f81b95d5d409847cb50b7f3d4e` |
| #147 | `678cf849512963b806ed21411a72a12853fd768e` |
| #148 | `5a8fc462c291d80cfb65f1ec0ac8bec94a7998ac` |
