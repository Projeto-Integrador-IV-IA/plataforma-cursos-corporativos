"""Regras de transicao do pipeline (RF05, RF06).

Concentra a decisao de "esta transicao e valida?" em um unico lugar, fora das
rotas e do repositorio, para poder ser testada isoladamente.

Regras acordadas:
    - avanco: apenas para a etapa imediatamente seguinte;
    - retrocesso: livre para qualquer etapa anterior (RF06), sempre registrado;
    - transicao para a mesma etapa e no-op e nao gera registro;
    - demanda com status diferente de ABERTA nao muda de etapa;
    - toda transicao valida exige autor e instante (RF07).

TODO(scaffolding): implementar ``can_transition()`` e ``next_stage()``.
"""

# TODO: def can_transition(current, target, status) -> bool: ...
