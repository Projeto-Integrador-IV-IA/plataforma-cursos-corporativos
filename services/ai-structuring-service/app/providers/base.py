"""Contrato do provedor de LLM.

Abstrai qual API de linguagem esta em uso. O restante do servico depende desta
interface, nunca de um SDK especifico - trocar de provedor nao pode obrigar a
reescrever a estruturacao (RNF13).

Contrato previsto:
    - metodo de completacao que recebe prompt, schema de saida e parametros;
    - devolve o texto/objeto e os metadados de uso (tokens, latencia, modelo),
      insumo do levantamento de custo de operacao (RNF12) e das metricas (RNF04);
    - falha e timeout viram excecao tipada, tratada em ``app.core.exceptions``
      (RNF05).

TODO(scaffolding): definir o Protocol/ABC do provedor.
"""
