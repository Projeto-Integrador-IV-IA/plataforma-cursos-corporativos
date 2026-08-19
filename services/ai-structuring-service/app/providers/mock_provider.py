"""Provedor falso, para desenvolvimento e testes.

Devolve saidas fixas e validas segundo o schema, sem chamar API externa.

Serve para: rodar a CI sem chave e sem custo (RNF12), testar o caminho de erro
e de timeout de forma deterministica (RNF05), e permitir que frontend e backend
avancem sem depender do provedor real.

Selecionado por ``LLM_PROVIDER=mock``.

TODO(scaffolding): implementar o provedor falso.
"""
