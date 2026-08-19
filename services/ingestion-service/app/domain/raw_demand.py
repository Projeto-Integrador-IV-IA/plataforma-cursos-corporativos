"""Dominio da demanda bruta (RF09).

Uma demanda bruta e um texto heterogeneo colado pelo operador: corpo de e-mail,
transcricao de reuniao, sequencia de mensagens de WhatsApp ou anotacao livre.
Nao ha formato garantido - e exatamente isso que a camada de IA precisa
resolver.

Conceitos:
    RawDemand        conteudo original, integro, exatamente como recebido
    SourceKind       origem declarada: EMAIL, TRANSCRICAO, MENSAGENS, ANOTACAO, OUTRO
    NormalizedText   texto limpo e pronto para o prompt (RF10)

Invariante central (RNF05): o conteudo original nunca e descartado nem alterado
pela normalizacao - normalizar produz um novo texto, nao substitui o de entrada.

TODO(scaffolding): implementar as estruturas do dominio.
"""
