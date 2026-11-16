"""Clientes HTTP para os demais microsservicos da plataforma.

Distinto de ``app/providers``: aqui mora a comunicacao entre servicos do
proprio projeto (RNF01), nao com o fornecedor de LLM. A separacao existe
porque sao dois eixos diferentes de troca - o provedor de IA e configuracao
(RNF03); o endereco do `pipeline-service` e topologia da composicao - e o
teste de arquitetura de `app/providers` (`test_provider_isolation.py`) os
trata como pacotes igualmente autorizados a importar um cliente HTTP
generico.
"""
