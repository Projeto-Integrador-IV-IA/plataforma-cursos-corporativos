# Custos de operação

Atende **RNF12**: operação em camada gratuita/estudantil, com o consumo de API de linguagem como **única despesa recorrente controlada**. Levantamento é entregável da 3ª parcial (20/10) e atende ao card **#121**.

> ⚠️ **Premissa de Data e Valores:** Consulta realizada em **09/10/2026**. Os preços de APIs de terceiros estão sujeitos a alterações e as estimativas baseiam-se em premissas de volume declaradas.

## Premissa

O projeto opera com custo próximo de zero. Qualquer item pago entra somente com aprovação da gerência e registro aqui.

## Estrutura de custo e Infraestrutura

| Item | Estratégia | Custo esperado | Comportamento ao estourar o Free Tier |
|---|---|---|---|
| Repositório e CI | GitHub, plano gratuito | R$ 0 | Limites generosos de minutos de CI (2000 min/mês). Se estourar, aguarda o ciclo mensal. |
| Banco de dados | PostgreSQL local em container; camada gratuita na homologação (Supabase/Render) | R$ 0 | O banco entra em modo somente leitura ou suspende após inatividade. Mitigação: Alerta e migração para plano básico (~$7/mês). |
| Hospedagem do backend | Camada gratuita/estudantil — provedor a definir ([Q5](../01-requisitos/questoes-em-aberto.md#q5--ambiente-de-homologação)) | R$ 0 | Instâncias entram em repouso (*spin down*) sem requisições. Mitigação: Health checks periódicos. |
| Hospedagem do frontend | Build estático em camada gratuita (Vercel/Netlify) | R$ 0 | Franquia generosa de banda. Cobrança por GB excedente se ultrapassar cotas de dezenas de GBs. |
| **API de linguagem (LLM)** | **Único custo recorrente** (OpenRouter / Modelos) | Variável (Camada gratuita / promocional ou baixo custo) | Interrupção da chave ou necessidade de recarga de créditos pré-pagos. |

## Premissas de Volume (Carga de Trabalho Estimada)

Para dimensionar o custo mensal da API e dos serviços, adota-se o cenário de operação:
- **Propostas / Demandas criadas por dia:** ~50 demandas/dia (~1.500 mensais) ou cenário base de 2 a 3 demandas do cliente real.
- **Fontes brutas por demanda:** 3 fontes (média de e-mails, transcrições e WhatsApp).
- **Volume de Áudio STT (Speech-to-Text / RF30):** 10 horas/mês para transcrição de reuniões longas.

## Como estimar o custo da API de LLM

O custo é proporcional aos tokens consumidos. A estimativa por demanda é:

custo_por_demanda = (tokens_entrada  × preço_entrada)
+ (tokens_saída    × preço_saída)

Como são duas chamadas encadeadas (extração e geração), o custo de uma demanda é a soma das duas.

**A instrumentação já está prevista:** `artifact_versions.metadados_ia` grava tokens de entrada, tokens de saída e latência de cada geração. O custo real sai desses dados, não de estimativa de papel — é o que torna este levantamento verificável na 3ª parcial.

### Custo de STT (Speech-to-Text / ElevenLabs ou Similar)

O STT é o item unitário mais caro do novo escopo para conversão de áudio em texto bruto:
- **Custo estimado:** Aprox. \$0.006 por minuto de áudio (~\$0.36 por hora).
- **Projeção mensal (10 horas):** 10h $\times$ 60 min $\times$ \$0.006 = **Aprox. \$3.60 / mês**.

### Planilha a preencher na Fase 3

| Grandeza | Valor | Fonte |
|---|---|---|
| Tokens de entrada por demanda (média) | ~2.000 tokens | Medição sobre o conjunto de avaliação |
| Tokens de saída por demanda (média) | ~1.000 tokens | Medição |
| Custo estimado da API de LLM | \$0.00 a \$2.70 / mês | OpenRouter (Modelos Llama/Sonnet free/tier) |
| Custo estimado de STT (10h) | \$3.60 / mês | Provedor de transcrição |
| **Custo mensal total projetado** | **Aprox. \$3.60 a \$6.30** | Soma consolidada (22 dias úteis) |

## Controles de custo já embutidos no projeto

| Controle | Onde |
|---|---|
| Provedor falso (`LLM_PROVIDER=mock`) na CI e nos testes — nenhuma execução automatizada gasta chamada paga | `app/providers/mock_provider.py` |
| Validação de entrada antes de chamar o LLM — entrada vazia ou irrelevante não vira token | `structuring_service.py` |
| Retentativa limitada por `LLM_MAX_RETRIES` — falha não vira laço caro | Configuração |
| Truncamento do texto de entrada com registro — demanda gigante não vira conta gigante | `text_normalizer.py` |
| Extração e geração separadas — se a extração falha, a ementa nem é tentada | [Estratégia](estrategia-estruturacao.md#abordagem-duas-etapas-encadeadas) |

## Sustentação pós-MVP

No escopo acadêmico, a sustentação é a infraestrutura de baixo custo. Na continuidade comercial, o modelo previsto é **assinatura da plataforma (SaaS)** paga pela empresa cliente — ver [modelo de negócio](../00-produto/modelo-negocio.md).

O argumento econômico do projeto é direto: o benefício (tempo do operador liberado, com 2–3 propostas montadas manualmente por dia) precisa superar o custo de operação. É o cálculo que fecha a viabilidade e que deve ser apresentado na banca com número medido, não estimado.
