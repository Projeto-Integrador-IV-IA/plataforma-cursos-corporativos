# 4ª parcial — 17/11

**Marco M4** — Microsserviços integrados e MVP funcional end-to-end.

## Integração (21/10–07/11)

- [x] Os quatro serviços comunicando-se por API (RNF01) — verificado ao vivo em 17/11/2026 contra a
      stack real (`docker compose up`), não só em teste isolado por serviço.
- [x] Fluxo completo funcionando: login → cliente → demanda → texto bruto → estruturação → revisão →
      pipeline → artefatos versionados — inclusive a decisão de revisão (RF19.2), fechada nesta
      entrega.
- [x] Evidência visual do fluxo em navegador real — [capturas-18-11-2026](capturas-18-11-2026/)
      (login, visão geral, clientes, demandas, quadro do pipeline, detalhe da demanda e a tela de
      decisão de revisão do RF19.2), tiradas em 18/11/2026 num Chromium real via Playwright — não
      `curl`/script, que não aplicam CORS e por isso não teriam pego o bug de CORS corrigido em
      17/11/2026. É a confirmação direta de que a correção funciona num navegador de verdade.
      Capturas 10–13 usam um cliente e uma captação fictícios criados via chamada direta à API
      (não pela interface) — "Metalúrgica Vale do Aço Ltda", pedido de treinamento NR-12 por
      e-mail — para mostrar o resultado da estruturação citando a evidência do texto de origem de
      verdade, em vez dos dados de carga de teste ("Cliente de medicao"). A captura 13 usa o
      provedor mock (`LLM_PROVIDER=mock`), que devolve sempre a mesma estrutura fixa — o texto foi
      escrito para coincidir tematicamente com essa saída fixa, não prova que o modelo leu o texto.
      A captura
      [14-estruturacao-PROVEDOR-REAL-openrouter.png](capturas-18-11-2026/14-estruturacao-PROVEDOR-REAL-openrouter.png)
      é a prova disso: mesma demanda, provedor real ligado brevemente em 18/11/2026
      (`openrouter`/`deepseek-chat-v3.1`, `provider_latency_ms≈19,5s`) — o resultado muda
      visivelmente (campos ausentes reconhecidos como "Não informado" em vez de preenchidos,
      ementa derivada do texto real), confirmando que a chamada de fato acontece e lê o texto.
      Chave revogada e provedor revertido para mock logo em seguida (ver nota no `.env`).
- [x] Reprocessamento gera nova versão do mesmo artefato em vez de um artefato irmão (RF08, RF13,
      RF17) — **bug achado e corrigido em 18/11/2026**: `job_service.py` sempre criava um artefato
      novo a cada execução da IA, nunca chamava o `reprocess()` já existente e testado no
      pipeline-service; rodar "Fazer o curso com IA" duas vezes na mesma demanda duplicava o
      artefato em vez de versioná-lo. Corrigido consultando se já existe artefato do tipo antes de
      decidir entre criar e reprocessar (`PipelineServiceClient.find_artifact_id`); confirmado ao
      vivo (segunda execução virou versão 2 do mesmo artefato) e coberto em
      [`test_job_service_persistence.py`](../../services/ai-structuring-service/tests/unit/test_job_service_persistence.py).
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

- [x] Latência do CRUD medida — confronto com RNF07 — **medido ao vivo em 18/11/2026** contra a
      stack real: seis rotas do `pipeline-service` via gateway, 20 repetições cada, entre
      p50 = 28 ms e p95 = 440 ms — todas dentro do alvo de 500 ms. RNF07 passou de ⬜ para 🟢 na
      matriz. Amostra local, sem volume de produção — ver
      [Q2 em questões em aberto](../01-requisitos/questoes-em-aberto.md#q2--metas-de-desempenho).
- [x] Latência da estruturação medida — confronto com RNF06 — `total_elapsed_ms` exposto pela API;
      medição contra provedor real já existe (04/11/2026, OpenRouter, `deepseek-chat-v3.1`): p50 =
      11,6 s, p95 = 12,8 s, dentro do alvo de 15 s. RNF06 segue 🟡 (não 🟢) porque a amostra é
      pequena (3 casos sintéticos) e o ambiente de demonstração de hoje roda com provedor mock.
- [x] Desvios em relação às metas explicados e justificados — **nenhum desvio**: os dois alvos foram
      cumpridos nas medições disponíveis. A ressalva em ambos os casos é tamanho de amostra, não
      estouro de meta.

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
