"""Metricas de qualidade da estruturacao (RNF04).

Sao o entregavel verificavel da 3a parcial (20/10). Sem definicao explicita do
que se mede, a entrega nao tem como ser avaliada - ver
docs/04-ia/metricas-qualidade.md.

Metricas previstas:
    acuracia_de_extracao     por campo (RF11): valor extraido confere com o
                             gabarito anotado por humano
    cobertura_de_campos      proporcao de campos preenchidos quando a
                             informacao existe no texto
    taxa_de_alucinacao       campos preenchidos sem base no texto de entrada
    consistencia             mesma entrada, execucoes repetidas, mesma saida
                             (RNF03)
    conformidade_de_schema   proporcao de respostas validas de primeira
    coerencia_de_ementa      avaliacao humana em escala definida (RF12)
    latencia_p50_p95         tempo de resposta ponta a ponta (RNF06)
    custo_por_demanda        tokens e valor estimado por estruturacao (RNF12)

TODO(scaffolding): implementar o calculo das metricas.
"""
