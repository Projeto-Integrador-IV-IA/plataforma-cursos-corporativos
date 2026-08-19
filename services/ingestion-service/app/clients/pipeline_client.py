"""Cliente HTTP do pipeline-service.

Este servico nao acessa o banco do pipeline - fala apenas por API (RNF01, RNF13).

Operacoes previstas:
    - persistir a demanda bruta assim que ela chega, ANTES de qualquer chamada
      ao LLM (RNF05: falha do LLM nao pode perder a demanda ja registrada);
    - anexar o resultado estruturado como artefato da negociacao (RF13).

Comportamento em falha: erro do pipeline e erro da ingestao - a requisicao
falha de forma explicita, sem descartar o conteudo enviado pelo operador.

TODO(scaffolding): implementar o cliente.
"""
