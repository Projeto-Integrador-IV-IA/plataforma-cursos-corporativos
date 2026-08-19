"""Cliente HTTP do ai-structuring-service.

Envia o texto normalizado para estruturacao e devolve o curso estruturado.

Requisitos que moldam este cliente:
    - RNF06: alvo de resposta util em ate 15 s, com estado de processamento
      visivel ao operador (RF17);
    - RNF05: timeout e erro do LLM sao tratados como falha recuperavel - a
      demanda bruta permanece registrada e a estruturacao pode ser repetida.

TODO(scaffolding): implementar o cliente.
"""
