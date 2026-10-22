# Custos de operação

Atende **RNF23** (correspondente ao **RNF12** do Documento Consolidado v1.0): levantamento de custos operacionais e viabilidade de operação em camada gratuita/estudantil, com o consumo de API de linguagem como **única despesa recorrente controlada**. Entregável da 3ª parcial (20/10) — card **#121**.

> ⚠️ **Premissa de Data e Valores:** Consulta realizada em **09/10/2026**. Os preços de APIs de terceiros estão sujeitos a alterações e as estimativas baseiam-se em premissas de volume declaradas.

## Premissa

O projeto opera com custo próximo de zero. Qualquer item pago entra somente com aprovação da gerência e registro aqui.

## Estrutura de custo, Infraestrutura e Limites de Free Tier

| Item | Estratégia | Custo esperado | Comportamento ao estourar o Free Tier / Limites |
|---|---|---|---|
| Repositório e CI | GitHub, plano gratuito (repositório público) | R$ 0 | Ações de CI em repositórios públicos em runners padrão possuem recursos ilimitados, sem consumo restrito da franquia de 2.000 min de repositórios privados. |
| Armazenamento (Banco/Arquivos) | Supabase / Render (Tier Gratuito: até 500MB) | R$ 0 | O banco entra em modo somente leitura ou suspende após inatividade. **Mitigação:** Alerta em 80% de uso e migração para plano básico (~$7/mês). |
| Hospedagem do backend | Camada gratuita/estudantil — provedor a definir ([Q5](../01-requisitos/questoes-em-aberto.md#q5--ambiente-de-homologação)) | R$ 0 | Instâncias entram em repouso (*spin down*) sem requisições, gerando latência na primeira chamada. **Mitigação:** Health checks periódicos. |
| Hospedagem do frontend | Build estático em camada gratuita (Vercel/Netlify) | R$ 0 | Franquia generosa de banda. Cobrança por GB excedente apenas se ultrapassar cotas elevadas. |
| **API de LLM** | OpenRouter (Modelos Llama / Sonnet) | Variável (Gratuito a baixo custo) | Interrupção da chave ou necessidade de recarga de créditos pré-pagos. |
| **STT (Speech-to-Text)** | OpenAI Whisper API / Provedor compatível | ~\$3.60 / mês | Esgotamento de créditos da conta de API, exigindo recarga pré-paga para novas transcrições. |

## Premissas de Volume (Carga de Trabalho Estimada)

Para dimensionar o custo mensal, adota-se o **cenário base operacional de 2 a 3 demandas por dia do cliente real** (~55 demandas mensais úteis), utilizando o cenário de 50 demandas/dia apenas como teste de sensibilidade de pico:
- **Fontes brutas por demanda:** 3 fontes em média (e-mails, transcrições e WhatsApp).
- **Chamadas de LLM por demanda:** 2 chamadas encadeadas (extração e geração).
- **Consumo de tokens por chamada individual:** ~1.000 tokens de entrada e ~500 de saída por chamada (totalizando o agregado por demanda de ~2.000 tokens de entrada e ~1.000 tokens de saída).
- **Volume de Áudio STT:** 10 horas/mês de conversão de áudio de reuniões.

## Como estimar o custo da API de LLM (Reproduzível)

O custo é proporcional aos tokens consumidos. A fórmula de cálculo por demanda é:

```text
custo_por_demanda = (tokens_entrada  × preço_entrada_por_token)
                  + (tokens_saída    × preço_saída_por_token)

### Preços Unitários de Referência por Modelo (OpenRouter / APIs)

- **Llama 3.3 70B (Promocional / Free Tier):** US$ 0.00 / MTokens (Entrada e Saída).
- **Claude 3.5 Sonnet:** US$ 3.00 por 1M tokens de entrada (US$ 0.003 / 1k) e US$ 15.00 por 1M tokens de saída (US$ 0.015 / 1k).

Aplicando o cenário base (55 demandas mensais $\times$ 2.000 tokens de entrada e 1.000 de saída) sobre o modelo pago de referência (Claude 3.5 Sonnet):

- **Entrada:** 55 $\times$ 2.000 = 110.000 tokens $\rightarrow$ $\approx$ US$ 0,33
- **Saída:** 55 $\times$ 1.000 = 55.000 tokens $\rightarrow$ $\approx$US$ 0,82
- **Total estimado LLM:** $\approx$ US$ 1,15 a US$ 2,70 / mês (conforme variação de volume).

### Custo de STT (Speech-to-Text / OpenAI Whisper API)

- **Fonte e dados de consulta:** OpenAI Whisper API Pricing (US$ 0,006 por minuto de áudio). Consulta em 09/10/2026.
- **Projeção mensal (10 horas / 600 minutos):**
  $$10\text{h} \times 60\text{min} \times \text{US\$ } 0{,}006 = \text{US\$ } 3{,}60 \text{ / mês}$$

---

## Estimativa Consolidada (A confirmação por medição)

| Grandeza / Serviço | Valor | Fonte / Base de Dados |
|---|---|---|
| **Custo estimado da API de LLM** | US$ 0.00 a US$ 2.70 / mês | OpenRouter (Llama free / Sonnet pago) |
| **Custo estimado de STT (10h)** | US$ 3.60 / mês | OpenAI Whisper API (US$ 0.006/min) |
| **Custo mensal total projetado** | **Aprox. US$ 3.60 a US$ 6.30** | Soma consolidada para o cenário operacional |

*Nota: O número real e medido substituirá esta estimativa na 3ª parcial, através da instrumentação do card **#22** (`artifact_versions.metadados_ia`).*

---

## Controles de custo já embutidos no projeto

| Controle | Onde |
|---|---|
| Provedor falso (`LLM_PROVIDER=mock`) na CI e nos testes — nenhuma execução automatizada gasta chamada paga | `app/providers/mock_provider.py` |
| Validação de entrada antes de chamar o LLM — entrada vazia ou irrelevante não vira token | `structuring_service.py` |
| Retentativa limitada por `LLM_MAX_RETRIES` — falha não vira laço caro | Configuração |
| Truncamento do texto de entrada com registro — demanda gigante não vira conta gigante | `text_normalizer.py` |
| Extração e geração separadas — se a extração falha, a ementa nem é tentada | [Estratégia](estrategia-estruturacao.md#abordagem-duas-etapas-encadeadas) |

---

## Sustentação pós-MVP

No escopo acadêmico, a sustentação é a infraestrutura de baixo custo. Na continuidade comercial, o modelo previsto é **assinatura da plataforma (SaaS)** paga pela empresa cliente — ver [modelo de negócio](../00-produto/modelo-negocio.md).

O argumento econômico do projeto é direto: o benefício (tempo do operador liberado, com 2–3 propostas montadas manualmente por dia) precisa superar o custo de operação. É o cálculo que fecha a viabilidade e que deve ser apresentado na banca com número medido, não estimado.

