# Definition of Done

Um card só vai para *Done* quando **todos** os itens aplicáveis estão cumpridos. Não existe "quase
pronto" — item pendente significa card em andamento.

## Para qualquer card

- [ ] O requisito do card está atendido conforme descrito, sem ampliar nem reduzir escopo
- [ ] Os critérios de aceite do card foram verificados um a um
- [ ] `make check` passa localmente (lint + testes)
- [ ] CI verde no PR
- [ ] Revisado e aprovado conforme o [fluxo](fluxo-git.md#5-review)
- [ ] Nenhum segredo commitado (RNF11)
- [ ] Configuração sensível lida somente do ambiente e senhas armazenadas como hash (RNF11)
- [ ] [Matriz de rastreabilidade](../01-requisitos/matriz-rastreabilidade.md) atualizada
- [ ] Nada de código comentado, `console.log` esquecido ou `TODO` sem card correspondente

## Card de backend

- [ ] Rota implementada conforme o contrato OpenAPI — implementação diverge do contrato é defeito,
      não "detalhe"
- [ ] [Contrato](../../packages/contracts) atualizado no mesmo PR, se a API mudou (RNF02)
- [ ] Migration criada e testada nos dois sentidos (`upgrade` e `downgrade`), se o modelo mudou
- [ ] Teste do caminho feliz **e** de ao menos um caminho de erro
- [ ] Erro tratado retorna o formato padronizado da plataforma
- [ ] Rota protegida por autenticação, salvo exceção justificada (RNF10)

## Card de frontend

- [ ] Tela funciona integrada à API real, não a dado fixo
- [ ] Estados de carregamento, erro e vazio tratados — os três, não só o feliz
- [ ] Feedback visível durante a estruturação por IA, quando aplicável (RF17)
- [ ] Sem `any` no TypeScript
- [ ] Navegável por teclado; rótulos associados aos campos de formulário

## Card de IA

- [ ] Prompt versionado em arquivo próprio, com metadados preenchidos (RNF03)
- [ ] Saída validada contra o JSON Schema
- [ ] Caminho de falha e de timeout tratado sem perder a demanda bruta (RNF05)
- [ ] Avaliação executada sobre o conjunto e relatório publicado em
      [`avaliacoes/`](../04-ia/avaliacoes) (RNF04)
- [ ] Tokens e latência instrumentados (RNF12)
- [ ] Testes rodam com `LLM_PROVIDER=mock`, sem gastar chamada paga

## Card de documentação

- [ ] Documento revisado por outro integrante
- [ ] Links internos funcionando
- [ ] Diagramas em Mermaid, versionados como texto
- [ ] IDs de requisito citados corretamente

## Para uma entrega parcial

- [ ] Todos os cards da fase em *Done*
- [ ] Checklist da entrega em [06-entregas](../06-entregas) cumprido
- [ ] Documentação da fase consolidada e revisada
- [ ] Demonstração ensaiada, com roteiro escrito
- [ ] Questões em aberto da fase resolvidas ou repactuadas com prazo novo

## Definition of Ready

Um card só entra na sprint se:

- [ ] Tem ID de requisito no título
- [ ] Tem critérios de aceite escritos e verificáveis
- [ ] Tem serviço e responsável definidos
- [ ] Não depende de decisão pendente em
      [questões em aberto](../01-requisitos/questoes-em-aberto.md)
- [ ] Cabe em uma sprint — se não cabe, é quebrado em cards menores antes de começar
