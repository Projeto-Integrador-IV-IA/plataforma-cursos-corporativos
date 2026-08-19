"""Encaminhamento de requisicoes aos servicos internos.

Responsabilidades:
    - repassar metodo, caminho, query, corpo e headers relevantes;
    - injetar a identidade do usuario autenticado e o ``X-Request-ID`` para
      rastrear o fluxo entre servicos (RNF09);
    - remover headers sensiveis do cliente antes do repasse (RNF10);
    - traduzir indisponibilidade do servico a jusante em erro padronizado
      (502/504), sem vazar detalhe de infraestrutura.

Timeouts distintos por destino: operacoes de CRM seguem RNF07 (alvo 500 ms);
a rota de estruturacao segue RNF06 (alvo 15 s).

TODO(scaffolding): implementar o encaminhamento.
"""
