"""Caso de uso: movimentacao no pipeline (RF05, RF06, RF07).

Fluxo de uma transicao:
    1. valida a transicao com ``app.domain.rules`` (avanco sequencial,
       retrocesso livre, status ABERTA);
    2. registra a ``StageTransition`` com autor, instante, origem e destino;
    3. atualiza a etapa corrente da demanda.

Os passos 2 e 3 ocorrem na mesma transacao: nenhuma transicao pode se perder e
o estado nunca diverge do historico (RNF09).

TODO(scaffolding): implementar.
"""
