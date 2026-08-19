# Custos de operação

Atende **RNF12**: operação em camada gratuita/estudantil, com o consumo de API de linguagem como
**única despesa recorrente controlada**. Levantamento é entregável da 3ª parcial (20/10).

## Premissa

O projeto opera com custo próximo de zero. Qualquer item pago entra somente com aprovação da
gerência e registro aqui.

## Estrutura de custo

| Item | Estratégia | Custo esperado |
|---|---|---|
| Repositório e CI | GitHub, plano gratuito | R$ 0 |
| Banco de dados | PostgreSQL local em container; camada gratuita na homologação | R$ 0 |
| Hospedagem do backend | Camada gratuita/estudantil — provedor a definir ([Q5](../01-requisitos/questoes-em-aberto.md#q5--ambiente-de-homologação)) | R$ 0 |
| Hospedagem do frontend | Build estático em camada gratuita | R$ 0 |
| **API de linguagem** | **Único custo recorrente** | A medir |

## Como estimar o custo da API

O custo é proporcional aos tokens consumidos. A estimativa por demanda é:

```
custo_por_demanda = (tokens_entrada  × preço_entrada)
                  + (tokens_saída    × preço_saída)
```

Como são duas chamadas encadeadas (extração e geração), o custo de uma demanda é a soma das duas.

**A instrumentação já está prevista:** `artifact_versions.metadados_ia` grava tokens de entrada,
tokens de saída e latência de cada geração. O custo real sai desses dados, não de estimativa de
papel — é o que torna este levantamento verificável na 3ª parcial.

### Planilha a preencher na Fase 3

| Grandeza | Valor | Fonte |
|---|---|---|
| Tokens de entrada por demanda (média) | | Medição sobre o conjunto de avaliação |
| Tokens de saída por demanda (média) | | Medição |
| Custo por demanda | | Cálculo |
| Demandas por dia (cliente real) | 2 a 3 | Levantamento com o cliente |
| **Custo mensal estimado** | | 22 dias úteis |
| Custo do desenvolvimento (testes e avaliação) | | Medição acumulada |

## Controles de custo já embutidos no projeto

| Controle | Onde |
|---|---|
| Provedor falso (`LLM_PROVIDER=mock`) na CI e nos testes — nenhuma execução automatizada gasta chamada paga | `app/providers/mock_provider.py` |
| Validação de entrada antes de chamar o LLM — entrada vazia ou irrelevante não vira token | `structuring_service.py` |
| Retentativa limitada por `LLM_MAX_RETRIES` — falha não vira laço caro | Configuração |
| Truncamento do texto de entrada com registro — demanda gigante não vira conta gigante | `text_normalizer.py` |
| Extração e geração separadas — se a extração falha, a ementa nem é tentada | [Estratégia](estrategia-estruturacao.md#abordagem-duas-etapas-encadeadas) |

## Sustentação pós-MVP

No escopo acadêmico, a sustentação é a infraestrutura de baixo custo. Na continuidade comercial, o
modelo previsto é **assinatura da plataforma (SaaS)** paga pela empresa cliente — ver
[modelo de negócio](../00-produto/modelo-negocio.md).

O argumento econômico do projeto é direto: o benefício (tempo do operador liberado, com 2–3 propostas
montadas manualmente por dia) precisa superar o custo de operação. É o cálculo que fecha a
viabilidade e que deve ser apresentado na banca com número medido, não estimado.
