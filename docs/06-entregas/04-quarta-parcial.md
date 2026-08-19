# 4ª parcial — 17/11

**Marco M4** — Microsserviços integrados e MVP funcional end-to-end.

## Integração (21/10–07/11)

- [ ] Os quatro serviços comunicando-se por API (RNF01)
- [ ] Fluxo completo funcionando: login → cliente → demanda → texto bruto → estruturação → revisão →
      pipeline → artefatos versionados
- [ ] Contratos de API consistentes entre serviços e frontend (RNF02)
- [ ] Testes end-to-end cobrindo o fluxo principal — [tests/e2e](../../tests)
- [ ] Correlação de log entre serviços funcionando (`X-Request-ID`)

## Testes e tratamento de exceção (28/10–14/11)

- [ ] LLM indisponível: demanda bruta preservada e operação repetível (RNF05)
- [ ] Transição inválida de etapa recusada, sem alterar o histórico
- [ ] Requisição sem token recusada em toda rota protegida (RNF10)
- [ ] Entrada inválida tratada com mensagem clara ao operador
- [ ] Serviço a jusante fora do ar tratado sem tela quebrada
- [ ] Estados de carregamento, erro e vazio tratados em todas as telas

## Desempenho

- [ ] Latência do CRUD medida — confronto com RNF07
- [ ] Latência da estruturação medida — confronto com RNF06
- [ ] Desvios em relação às metas explicados e justificados

## Verificação dos requisitos

- [ ] **Todos os RF Essenciais implementados e demonstráveis**
- [ ] RF de prioridade Alta implementados, ou ausência justificada
- [ ] RNF Essenciais atendidos e verificáveis
- [ ] Matriz de rastreabilidade 100% preenchida — sem linha em branco

## Segurança

- [ ] Nenhum segredo no repositório (RNF11)
- [ ] Dados de cliente não acessíveis sem autenticação (RNF10)
- [ ] Serviços internos não expostos publicamente
- [ ] Dados usados em teste e demonstração anonimizados

## Documentação (03–21/11)

- [ ] Relatório técnico redigido
- [ ] Documentação consolidada e coerente com o implementado
- [ ] READMEs dos serviços atualizados — sem "scaffolding" onde já há código
- [ ] Segunda rodada de avaliação da IA publicada (RNF04)
- [ ] Roteiro de demonstração escrito

## Homologação (17–23/11)

- [ ] Aplicação implantada em ambiente acessível (RNF15)
- [ ] Validação end-to-end com o cliente real
- [ ] Ajustes finais aplicados
- [ ] Apresentação ensaiada com controle de tempo
