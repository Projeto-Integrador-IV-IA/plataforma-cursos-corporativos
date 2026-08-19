"""Dominio do curso estruturado - o produto do nucleo inteligente (RF11, RF12).

Esta e a forma canonica da saida da IA. O schema e fixo e versionado: prompt,
validacao, contrato de API e frontend dependem dele (RNF03). Alterar campo aqui
e alterar contrato - ver packages/contracts/schemas/structured-course.schema.json.

Campos extraidos da demanda (RF11):
    tema                    assunto central do treinamento
    nicho                   setor ou area de atuacao do cliente
    publico_alvo            perfil dos participantes
    numero_participantes    quantidade estimada (pode ser faixa)
    carga_horaria           duracao total em horas
    formato                 presencial, online ou hibrido

Campos gerados (RF12):
    objetivos_aprendizagem  o que o participante sera capaz de fazer
    ementa                  modulos ordenados, cada um com titulo, topicos e carga

Metadados de confianca:
    campos_ausentes         o que nao foi possivel extrair do texto de entrada
    observacoes             ambiguidades que o operador precisa resolver

O modelo NUNCA inventa valor ausente: campo sem base no texto e reportado como
ausente, para que a revisao humana decida (RF14). Isso e o que torna RNF04
mensuravel.

TODO(scaffolding): implementar os modelos Pydantic do curso estruturado.
"""
