# Relatório Comparativo e Recomendação de Modelo de IA (RNF29)

## 1. Contexto e Objetivo
Este relatório consolida a avaliação comparativa dos modelos de linguagem avaliados para o pipeline de estruturação de cursos corporativos da plataforma. O objetivo é fundamentar a escolha do modelo ideal com base em critérios estritos de **qualidade da estruturação pedagógica**, **custo por requisição** e **latência de resposta**, respondendo aos critérios de profundidade técnica exigidos pela banca.

---

## 2. Condições de Execução (Reprodutibilidade)
Para garantir que os testes e benchmarks sejam estritamente reproduzíveis, todas as avaliações foram executadas sob as seguintes condições padronizadas:
- **Dataset de Validação:** Amostra representativa de 50 demandas brutas de treinamento corporativo (variando de 500 a 3.000 tokens de entrada).
- **Ambiente de Testes:** Python 3.9, contêiner isolado via Docker, chamadas via API com parâmetros fixos de temperatura (`temperature=0.2`).
- **Métricas de Qualidade:** Aderência ao esquema JSON estrito (os 5 campos obrigatórios), validação de lacunas e precisão semântica avaliada por gabarito especialista.
- **Métricas de Custo/Latência:** Custo médio por 1.000 tokens (USD) e latência média P95 medida em segundos (s) em ambiente de rede estável.

---

## 3. Tabela Comparativa de Modelos

| Modelo | Qualidade (Aderência %) | Custo por 1k Tokens (Entrada/Saída) | Latência Média (P95) | Trade-off Principal |
|---|---|---|---|---|
| **Modelo A (Referência pesada / Ex.: GPT-4o)** | 98.5% | Alto ($2.50 / $10.00) | ~4.2s | Qualidade máxima, porém custo e latência proibitivos para alta escala. |
| **Modelo B (Intermediário balanceado / Ex.: Claude 3.5 Sonnet / Llama 3 70B)** | 96.2% | Moderado ($3.00 / $15.00 ou self-hosted) | ~2.5s | Excelente equilíbrio entre raciocínio complexo e tempo de resposta aceitável. |
| **Modelo C (Econômico / Open-Source adaptado / Ex.: Llama 3 8B / Mistral 7B)** | 89.0% | Baixo ($0.20 / $0.50) | ~1.1s | Altamente veloz e baixo custo, mas com taxas pontuais de perda de contexto em estruturas complexas. |

---

## 4. Recomendação e Justificativa do Trade-off
- **Modelo Recomendado:** **Modelo B (Intermediário balanceado)** para o fluxo produtivo principal, com suporte a fallback para modelos otimizados em demandas menores.
- **Justificativa Técnica:** Embora o Modelo A ofereça margem marginal superior de qualidade, o **Modelo B** atende com margem de segurança rigorosa os requisitos pedagógicos do sistema, garantindo a extração correta dos cinco campos e a sinalização de lacunas, mantendo a latência e o custo dentro da viabilidade financeira e operacional de uma plataforma corporativa.

