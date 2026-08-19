"""Conjunto de avaliacao da estruturacao (RNF04).

Casos reais anonimizados do cliente, cada um com o texto bruto de entrada e o
gabarito anotado por um humano. E o que permite medir acuracia em vez de
opinar sobre a qualidade.

Regras:
    - dado de cliente sempre anonimizado antes de entrar no conjunto (RNF10);
    - o conjunto e versionado junto com o codigo, em tests/fixtures;
    - toda mudanca de prompt e reavaliada sobre o mesmo conjunto, senao os
      numeros nao sao comparaveis.

Meta minima: 20 casos anotados ate a 3a parcial (20/10).

TODO(scaffolding): implementar o carregamento do conjunto.
"""
