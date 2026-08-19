"""Normalizacao do texto bruto (RF10).

Prepara a entrada para a camada de IA sem interpretar conteudo - interpretacao
e trabalho do LLM, nao de regra fixa.

Transformacoes previstas:
    - normalizacao de espacos em branco, quebras de linha e caracteres invisiveis;
    - remocao de assinaturas, avisos legais e blocos de resposta encadeada de e-mail;
    - remocao de marcadores de transcricao automatica (carimbos de tempo, rotulos
      de locutor) preservando o que foi dito;
    - unificacao de codificacao em UTF-8;
    - corte por limite de tamanho, com registro de truncamento quando ocorrer.

O que NAO fazer aqui: extrair campos, inferir tema ou publico, resumir. Isso e
responsabilidade do ai-structuring-service (RF11, RF12).

TODO(scaffolding): implementar as funcoes de normalizacao.
"""
