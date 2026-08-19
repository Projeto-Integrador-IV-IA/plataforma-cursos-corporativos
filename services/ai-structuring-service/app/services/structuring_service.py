"""Caso de uso: estruturacao do curso por IA (RF11, RF12, RF13).

Fluxo:
    1. receber o texto normalizado e o identificador da demanda;
    2. montar o prompt versionado de extracao (RF11);
    3. chamar o provedor de LLM com schema de saida definido (RNF03);
    4. validar a resposta contra o JSON Schema - resposta invalida e falha,
       nao e aceita "quase certa";
    5. montar o prompt de ementa a partir dos requisitos extraidos (RF12);
    6. registrar metricas da execucao (RNF04) e custo estimado (RNF12);
    7. devolver o curso estruturado para anexacao a negociacao (RF13).

Tratamento de falha (RNF05): timeout, erro do provedor e saida invalida sao
reportados como falha recuperavel. O servico nao guarda a demanda bruta - quem
garante a persistencia previa e o ingestion-service.

TODO(scaffolding): implementar o caso de uso.
"""
