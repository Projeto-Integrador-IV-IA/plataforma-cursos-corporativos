"""Contrato base dos repositorios.

Isola o acesso a dados das regras de aplicacao: as rotas e os casos de uso
falam com repositorio, nunca com a sessao do SQLAlchemy diretamente. Isso
mantem os casos de uso testaveis sem banco.

Operacoes comuns previstas: get, list (com filtro e paginacao), add, update.
Repositorios de tabelas append-only (transicoes e versoes) expoem apenas
leitura e insercao - nao ha update nem delete (RNF09).

TODO(scaffolding): implementar o repositorio generico.
"""
