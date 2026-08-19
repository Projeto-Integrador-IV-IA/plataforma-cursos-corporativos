"""Emissao e validacao de token de acesso (RF16).

O gateway e o unico ponto que emite e valida token. Os servicos internos
confiam no gateway e nao reimplementam autenticacao - isso mantem uma unica
superficie de autenticacao para auditar (RNF10).

Contrato previsto:
    - token JWT assinado com ``JWT_SECRET_KEY`` (RNF11), algoritmo e expiracao
      vindos de configuracao;
    - claims minimas: sub (id do usuario), nome, papel, exp, iat;
    - validacao rejeita token expirado, assinatura invalida e claim ausente;
    - o identificador do usuario e propagado aos servicos internos por header,
      para sustentar a autoria da trilha de auditoria (RF07).

TODO(scaffolding): implementar emissao e validacao.
"""
