# 3ª parcial — 20/10

**Marco M3** — Backend e pipeline funcionais, módulo de estruturação integrado, métricas de
qualidade e levantamento de custos de operação.

## Backend base (16/09–03/10)

- [ ] `pipeline-service`: CRUD de clientes (RF01)
- [ ] `pipeline-service`: CRUD de demandas vinculadas a cliente (RF02)
- [ ] Listagem com filtro por status, cliente e período (RF03)
- [ ] Detalhe da negociação com histórico e artefatos (RF04)
- [ ] `gateway-service`: autenticação funcionando (RF16)
- [ ] Migrations aplicadas; integridade referencial verificada (RNF08)

## Pipeline e rastreabilidade (22/09–17/10)

- [ ] Avanço pelas cinco etapas (RF05)
- [ ] **Retrocesso livre** a etapas anteriores, com motivo (RF06)
- [ ] Histórico de transições registrando quem, quando, origem e destino (RF07)
- [ ] Versionamento de artefatos com recuperação de versão anterior (RF08)
- [ ] Consolidação documental por negociação (RF15)
- [ ] Verificado: nenhuma transição ou versão se perde (RNF09)

## Frontend (16/09–03/10)

- [ ] Tela de login (RF16)
- [ ] Cadastro e listagem de clientes (RF01, RF03)
- [ ] Cadastro e listagem de demandas (RF02, RF03)
- [ ] Tela de detalhe com pipeline visual e histórico (RF04, RF05)
- [ ] Formulário de ingestão de demanda bruta (RF09)

## Integração da IA (16/09–17/10)

- [ ] `ingestion-service` recebendo e normalizando texto livre (RF09, RF10)
- [ ] Demanda bruta persistida **antes** da chamada ao LLM — verificado por teste (RNF05)
- [ ] Extração de requisitos integrada (RF11)
- [ ] Geração de ementa integrada (RF12)
- [ ] Resultado anexado automaticamente à negociação (RF13)
- [ ] Revisão e edição da saída pelo operador (RF14)
- [ ] Estado de processamento visível na interface (RF17)
- [ ] Falha e timeout do LLM tratados sem perda da demanda (RNF05)
- [ ] Prompts refinados e versionados (RNF03)

## Métricas de qualidade (06–17/10) — RNF04

- [ ] Conjunto de avaliação com **20 casos anotados**
- [ ] Acurácia de extração medida por campo
- [ ] Taxa de alucinação medida
- [ ] Consistência medida (mesma entrada, execuções repetidas)
- [ ] Coerência da ementa avaliada por humano
- [ ] Latência p50/p95 medida — confronto com RNF06
- [ ] Relatório publicado em [avaliações](../04-ia/avaliacoes)

## Custos de operação (06–17/10) — RNF12

- [ ] Tokens por demanda medidos
- [ ] Custo por demanda calculado a partir de dado real
- [ ] Custo mensal projetado para o volume do cliente (2–3 demandas/dia)
- [ ] Custo de infraestrutura levantado
- [ ] [Documento de custos](../04-ia/custos-operacao.md) preenchido
- [ ] **Q5** — ambiente de homologação definido ([questões em aberto](../01-requisitos/questoes-em-aberto.md))

## Verificação antes de submeter

- [ ] Fluxo demonstrável ponta a ponta, mesmo que ainda não polido
- [ ] Matriz de rastreabilidade refletindo o implementado
- [ ] Cenários de falha testados, não só o caminho feliz
