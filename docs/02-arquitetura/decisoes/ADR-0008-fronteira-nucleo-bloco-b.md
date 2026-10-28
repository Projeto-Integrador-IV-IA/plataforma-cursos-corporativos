# ADR-0008 — Fronteira entre o núcleo do MVP e o Bloco B

- **Status:** Aceita
- **Data:** 2026-10-14
- **Requisitos:** RNF13 (nesta matriz; **RNF04** no Documento Consolidado v1.0), RF-F1 a RF-F5
- **Relacionadas:** [ADR-0001](ADR-0001-arquitetura-microsservicos.md), [ADR-0004](ADR-0004-banco-unico-com-dono.md)

## Contexto

O **Bloco B** reúne as evoluções que ficaram fora do MVP
([requisitos funcionais](../../01-requisitos/requisitos-funcionais.md)): sugestão orçamentária e
custeio (RF-F1), geração da proposta comercial (RF-F2), geração de slides (RF-F3), busca de
instrutores (RF-F4) e integrações externas (RF-F5). Implementar qualquer um deles durante o MVP é
desvio de escopo; todos voltam depois e precisam entrar **sem reescrever o núcleo** (RNF13).

A [ADR-0001](ADR-0001-arquitetura-microsservicos.md) promete isso — evoluções entram como serviço
novo, consumindo o `pipeline-service` por API — e a [ADR-0004](ADR-0004-banco-unico-com-dono.md)
dá a base: só o `pipeline-service` acessa o banco. Uma promessa de arquitetura sem verificação,
porém, se desfaz em atalhos pequenos: um campo `orcamento` "só por enquanto" num schema, um valor
de enum reservado "para a próxima fase". Cada atalho parece inofensivo; juntos, são a refatoração
do núcleo que a arquitetura desacoplada existia para evitar.

Até esta ADR, nada verificava automaticamente que o núcleo estava livre dos conceitos do Bloco B. O
argumento da arquitetura desacoplada dependia de intenção, não de evidência.

## Decisão

1. **A dependência tem uma direção só.** Módulos do Bloco B dependem do núcleo; o núcleo não chama,
   importa nem nomeia módulo do Bloco B. Código de produção, schemas, contratos, migrations e
   prompts do núcleo não modelam nem implementam custeio, instrutores, geração de proposta ou de
   slides — nem "desligados" ou "reservados".

2. **O ponto de extensão é o serviço novo.** Um módulo do Bloco B entra ao lado do núcleo:
   serviço próprio, contrato próprio em `packages/contracts`, cliente HTTP do `pipeline-service`
   (o padrão que o `ingestion-service` já usa), rota no `gateway-service`, entrada no Compose e
   feature própria no `web`. O resultado vira artefato da demanda quando for um documento. O passo
   a passo está em [visão geral](../visao-geral.md#ponto-de-extensão).

3. **A fronteira é verificada no CI.** O job `fronteira-bloco-b` do workflow de CI falha o PR se
   `custeio`, `orçamento`, `instrutor`, `proposta comercial` ou `slide` aparecerem em `services/`,
   `packages/` ou `web/`, exceto nos caminhos registrados em
   [`.github/fronteira-bloco-b-permitidos.txt`](../../../.github/fronteira-bloco-b-permitidos.txt),
   cada um com justificativa. A fala do cliente "depende do orçamento" — que aparece em exemplos
   de prompt e em fixtures, porque é o motivo de a carga horária ficar em aberto — é permitida em
   qualquer arquivo.

4. **Critério para classificar uma ocorrência.**

   | É vocabulário legítimo quando… | É vazamento quando… |
   |---|---|
   | nomeia a **etapa** `PROPOSTA` do pipeline (RF05) ou o **tipo de artefato** `PROPOSTA`: o ponto do processo e o documento que o operador anexa. O que é Bloco B é *gerar* esse documento (RF-F2). | cria campo, coluna, enum, endpoint, schema, prompt ou dependência para custeio, instrutor, geração de proposta ou de slides. |
   | aparece como **texto de cliente** em fixture de teste ou em exemplo de prompt (por exemplo, "depende do orçamento"). | uma regra do núcleo passa a tratar o conceito (validar, calcular, exibir). |
   | está num **teste que prova a fronteira**: o contrato recusa ou descarta campo do Bloco B. | o campo é aceito e guardado, mesmo que "opcional". |
   | está no diretório de um **módulo do Bloco B já aprovado** pela gerência. | está em arquivo do núcleo, mesmo num comentário que anuncia trabalho futuro. |

## Alternativas consideradas

| Alternativa | Por que não |
|---|---|
| **Só convenção e revisão de PR** | É o que existia. Fronteira sem teste volta a vazar: o revisor só enxerga o que está no diff. |
| **Reservar ganchos no núcleo** (campo `orcamento` nulo, tipo de artefato reservado, feature flag) | Antecipa o Bloco B dentro do núcleo — o oposto do objetivo — e é desvio de escopo. O custo de acoplar depois por serviço novo é menor que o custo de manter ganchos que ninguém exercita. |

## Consequências

**Positivas**

- A fronteira passa a ser **evidência**: o PR verde mostra que o núcleo está livre do Bloco B, e a
  justificativa da arquitetura desacoplada deixa de depender de intenção.
- Acoplar um módulo novo tem receita única e conhecida, o que reduz a discussão a cada evolução.
- Os testes que provam que o contrato recusa campo do Bloco B passam a ser reconhecidos como
  evidência, e não como ruído.

**Negativas — assumidas conscientemente**

- A busca é **léxica**, não semântica. Não pega o conceito escrito com outra palavra
  (`cost_estimate`, `preco`, `palestrante` usado como instrutor) e pode dar falso positivo em
  `slide` de CSS ou de biblioteca. A revisão de PR continua necessária; o job só impede o
  vazamento óbvio.
- A lista de permitidos libera **arquivos inteiros**, não linhas, porque número de linha muda a
  cada edição. Um vazamento dentro de um arquivo listado não é detectado. Por isso a lista deve
  conter apenas testes e diretórios de módulos, e cada entrada precisa de justificativa. Os
  prompts do núcleo ficam **fora** da lista de propósito: é onde um vazamento real seria mais
  provável, e só a frase do cliente acima é liberada neles.
- A liberação da frase "depende do orçamento" vale para qualquer arquivo. Uma regra de negócio
  que reaproveite essa expressão passaria sem aviso; a revisão de PR cobre esse caso.
- A lista precisa de manutenção: ao aprovar um módulo do Bloco B, o diretório dele entra na lista
  no mesmo PR que o cria.
- **Persistência própria de módulo não está decidida aqui.** Um módulo cujo dado não caiba em
  artefato precisa de armazenamento; se esse armazenamento é banco próprio do módulo é decisão
  da ADR que escopar o primeiro módulo, respeitando a [ADR-0004](ADR-0004-banco-unico-com-dono.md)
  (o núcleo continua com um único dono do banco).
