/**
 * Mapa de rotas da aplicacao.
 *
 * Rotas previstas:
 *   /login                        autenticacao (RF16)
 *   /clientes                     lista e cadastro de clientes (RF01, RF03)
 *   /clientes/:id                 detalhe do cliente
 *   /demandas                     lista com filtro por status, cliente, periodo (RF02, RF03)
 *   /demandas/:id                 detalhe: pipeline, historico e artefatos (RF04, RF05, RF06)
 *   /demandas/:id/ingestao        entrada de demanda bruta (RF09)
 *   /demandas/:id/estruturacao    revisao da saida da IA antes de uso externo (RF14)
 *   /artefatos/:id/versoes        historico de versoes (RF08)
 *
 * Toda rota, exceto /login, exige sessao autenticada (RNF10).
 *
 * TODO(scaffolding): implementar.
 */

export {};
