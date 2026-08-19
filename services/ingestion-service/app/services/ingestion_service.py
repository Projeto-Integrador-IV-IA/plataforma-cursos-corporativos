"""Caso de uso: ingestao de demanda heterogenea (RF09, RF10, RNF05).

Ordem obrigatoria das etapas:
    1. receber o texto bruto do formulario padronizado (RF09);
    2. persistir o bruto no pipeline-service - este passo vem primeiro e e
       inegociavel (RNF05);
    3. normalizar o texto (RF10);
    4. solicitar a estruturacao ao ai-structuring-service;
    5. anexar o resultado a negociacao (RF13) e reportar o estado ao chamador.

Se qualquer passo a partir do 3 falhar, o passo 2 ja garantiu que nada se
perdeu: a demanda fica registrada e pendente de estruturacao, e a operacao pode
ser repetida sem o operador colar o texto de novo.

TODO(scaffolding): implementar o caso de uso.
"""
