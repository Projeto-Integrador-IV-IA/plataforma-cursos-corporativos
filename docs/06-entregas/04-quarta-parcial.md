# 4ª parcial — 17/11

**Marco M4** — Microsserviços integrados e MVP funcional end-to-end.

## Integração (21/10–07/11)

- [x] Os quatro serviços comunicando-se por API (RNF01) — verificado ao vivo em 17/11/2026 contra a
      stack real (`docker compose up`), não só em teste isolado por serviço.
- [x] Fluxo completo funcionando: login → cliente → demanda → texto bruto → estruturação → revisão →
      pipeline → artefatos versionados — inclusive a decisão de revisão (RF19.2), fechada nesta
      entrega.
- [x] Contratos de API consistentes entre serviços e frontend (RNF02) — verificado por teste
      automatizado que compara cada contrato byte a byte contra o `/openapi.json` publicado por
      cada serviço (`test_versioned_contract_declares_every_published_operation` e equivalentes).
- [x] Testes end-to-end cobrindo o fluxo principal — [tests/e2e](../../tests) — escrito e verificado
      ao vivo em 17/11/2026 (antes desta data a pasta só tinha `.gitkeep`).
- [x] Correlação de log entre serviços funcionando (`X-Request-ID`) — **corrigido em 17/11/2026**:
      cada serviço já propagava e logava o cabeçalho quando ele chegava, mas nada o gerava quando
      ausente (o navegador nunca manda esse cabeçalho por conta própria), então a correlação nunca
      começava de fato. O gateway agora gera um identificador na borda quando a requisição chega
      sem um (`app/core/correlation.py`).

## Testes e tratamento de exceção (28/10–14/11)

- [x] LLM indisponível: demanda bruta preservada e operação repetível (RNF05) — verificado em
      [`test_structuring_jobs.py`](../../services/ai-structuring-service/tests/integration/test_structuring_jobs.py)
      (`_ProvedorQueFalha`); reproduzir contra a stack real exigiria reconfigurar o provedor em
      execução, o que descaracteriza o teste de integração entre serviços (ver `tests/README.md`).
- [x] Transição inválida de etapa recusada, sem alterar o histórico — verificado ao vivo
      (avançar a partir da última etapa recebe 409 e o histórico não ganha evento).
- [x] Requisição sem token recusada em toda rota protegida (RNF10) — verificado ao vivo.
- [x] Entrada inválida tratada com mensagem clara ao operador — coberto nas suítes de cada serviço
      (envelope de erro com `code`/`message`/`details.issues`).
- [x] Serviço a jusante fora do ar tratado sem tela quebrada — estados de erro com mensagem e
      "Tentar novamente" confirmados por auditoria de código em todas as telas principais.
- [x] Estados de carregamento, erro e vazio tratados em todas as telas — idem.

## Desempenho

- [ ] Latência do CRUD medida — confronto com RNF07 — **não medido**. RNF07 segue ⬜ na matriz.
- [ ] Latência da estruturação medida — confronto com RNF06 — `total_elapsed_ms` já é exposto pela
      API (RNF06 está 🟡), mas a aferição contra o alvo exige provedor de LLM real, não o mock da CI.
- [ ] Desvios em relação às metas explicados e justificados — depende dos dois itens acima.

## Verificação dos requisitos

- [ ] **Todos os RF Essenciais implementados e demonstráveis** — RF19.2 fechou nesta entrega; RF31
      (distinguir a fala do cliente na extração) segue ⬜ na matriz.
- [ ] RF de prioridade Alta implementados, ou ausência justificada — ver matriz para o detalhe
      linha a linha de cada um 🟡.
- [ ] RNF Essenciais atendidos e verificáveis — RNF07 (desempenho do CRM) segue ⬜, sem medição.
- [x] Matriz de rastreabilidade 100% preenchida — sem linha em branco — confirmado por verificação
      automatizada (nenhuma linha RF/RNF sem um dos quatro status).

## Segurança

- [x] Nenhum segredo no repositório (RNF11) — o job de verificação de segredos da CI falsamente
      aponta DSN com placeholder no histórico; sem segredo real versionado.
- [x] Dados de cliente não acessíveis sem autenticação (RNF10) — verificado ao vivo.
- [x] Serviços internos não expostos publicamente — confirmado: só o gateway publica porta no
      `docker-compose.yml`; os demais usam `expose` (rede interna). **Risco residual documentado**:
      nenhuma rota de pipeline/ingestion/ai-structuring valida a chamada além de confiar no gateway
      — depende de a topologia de rede (aqui, Docker) continuar isolando-os.
- [x] Dados usados em teste e demonstração anonimizados — dados fictícios em todos os testes e no
      roteiro de demonstração.

## Documentação (03–21/11)

- [x] Relatório técnico redigido — [relatorio-tecnico.md](relatorio-tecnico.md).
- [x] Documentação consolidada e coerente com o implementado — matriz revisada linha a linha nesta
      entrega e em 17/11/2026, incluindo a correção de reivindicações desatualizadas.
- [x] READMEs dos serviços atualizados — sem "scaffolding" onde já há código — corrigido em
      17/11/2026 (README raiz e READMEs de `web/src/features/{clients,demands,artifacts}`).
- [x] Segunda rodada de avaliação da IA publicada (RNF04) —
      [relatorio-comparativo-modelos.md](../04-ia/avaliacoes/relatorio-comparativo-modelos.md),
      medição real contra três modelos via OpenRouter.
- [x] Roteiro de demonstração escrito — [roteiro-demonstracao.md](roteiro-demonstracao.md).

## Homologação (17–23/11)

- [ ] Aplicação implantada em ambiente acessível (RNF15) — **decisão registrada em 17/11/2026**: para
      esta entrega e a banca, o ambiente de homologação é a própria stack local via
      `docker compose up`, apresentada por compartilhamento de tela — não há implantação em nuvem.
      Ver [questoes-em-aberto.md](../01-requisitos/questoes-em-aberto.md#q5--ambiente-de-homologação)
      para a justificativa completa. Item permanece ⬜ porque o checklist pede "ambiente acessível"
      (implica alcançável sem a máquina de quem apresenta), que esta decisão não cumpre — é a
      limitação assumida, não a tarefa concluída.
- [ ] Validação end-to-end com o cliente real — pendente, depende de agenda com o cliente.
- [ ] Ajustes finais aplicados — em andamento.
- [ ] Apresentação ensaiada com controle de tempo — pendente.
