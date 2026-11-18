Lógica de interface deste domínio: componentes de tela, hooks de dados e
formulários. Componentes genéricos (botão, tabela, modal) ficam em `src/components`.

Implementado: cadastro e listagem de demandas (RF02, RF03); detalhe com histórico de etapas,
fontes e artefatos (RF04, `DemandDetailView`); revisão da estrutura gerada por IA com evidência
por campo e decisão de aprovar/rejeitar/devolver (RF14, RF19.2, `DemandStructuringView` e
`DemandStructuringReview`). Movimentação de etapa (avançar/retroceder) fica em
`features/pipeline`, não aqui.
