Lógica de interface deste domínio: componentes de tela, hooks de dados e
formulários. Componentes genéricos (botão, tabela, modal) ficam em `src/components`.

`RequireSession` protege as rotas contra sessões ausentes ou expiradas.
`Authorization` lê o perfil da sessão, filtra ações e navegação e protege rotas
com uma lista de permissões. Até a matriz de RNF18 ser publicada, `OPERADOR` é o
único perfil conhecido e mantém as operações existentes; perfis desconhecidos
não recebem permissões. A API continua sendo a barreira efetiva: controles no
frontend servem apenas para não oferecer caminhos indisponíveis.
