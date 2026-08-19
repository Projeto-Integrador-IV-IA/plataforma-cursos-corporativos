# Métricas de qualidade da estruturação

Atende **RNF04**: métricas de acurácia e consistência mensuráveis e reportáveis — **entregável da
3ª parcial (20/10)**.

> ⚠️ **Sem definição explícita do que se mede e de como se coleta, a 3ª parcial não tem entregável
> verificável.** É a questão mais crítica em aberto do projeto — ver
> [Q3](../01-requisitos/questoes-em-aberto.md#q3--definição-da-métrica-de-qualidade-da-ia).

## Conjunto de avaliação

Nada se mede sem gabarito. O conjunto é a base de tudo o que vem abaixo.

| Item | Definição |
|---|---|
| **Origem** | Demandas reais do cliente (e-mails, transcrições, mensagens). |
| **Anonimização** | Nomes de empresa, pessoas, valores e contatos substituídos **antes** de entrar no repositório (RNF10). |
| **Gabarito** | Para cada caso, a saída correta anotada por um humano. |
| **Meta** | 20 casos anotados até 06/10. |
| **Onde** | [`tests/fixtures/`](../../tests/fixtures), versionado com o código. |

Toda mudança de prompt é reavaliada sobre **o mesmo conjunto**. Conjunto que muda entre medições
torna os números incomparáveis — e a comparação é o ponto.

## Métricas

### Extração de requisitos (RF11)

| Métrica | Como se calcula | Meta inicial |
|---|---|---|
| **Acurácia por campo** | Por campo (tema, nicho, público, participantes, carga, formato): proporção de casos em que o valor extraído bate com o gabarito. | ≥ 80% nos campos essenciais |
| **Acurácia global** | Média das acurácias por campo. | ≥ 75% |
| **Cobertura** | Proporção de campos preenchidos **quando a informação existe** no texto. | ≥ 85% |
| **Taxa de alucinação** | Proporção de campos preenchidos **sem base** no texto. Métrica de erro: quanto menor, melhor. | ≤ 5% |
| **Reconhecimento de ausência** | Proporção de campos corretamente marcados como ausentes quando a informação não está no texto. | ≥ 90% |

Cobertura e alucinação são o par que importa: um modelo pode maximizar cobertura simplesmente
chutando. A taxa de alucinação é o contrapeso — por isso as duas são sempre reportadas juntas.

**Comparação de valores** — critério a fixar antes da primeira medição:

- campos numéricos (participantes, carga horária): igualdade exata, ou tolerância declarada;
- campos textuais curtos (formato): correspondência exata sobre vocabulário fechado;
- campos textuais livres (tema, nicho, público): equivalência semântica julgada por humano — dois
  avaliadores, discordância resolvida por um terceiro.

### Geração de ementa (RF12)

Não há gabarito único: ementas diferentes podem estar igualmente corretas. Avaliação humana, em
escala de 1 a 5:

| Critério | Pergunta |
|---|---|
| **Coerência com os requisitos** | A ementa corresponde ao tema, público e carga extraídos? |
| **Adequação ao público** | O nível corresponde ao perfil declarado dos participantes? |
| **Consistência de carga** | A soma da carga dos módulos fecha com a carga total? |
| **Qualidade dos objetivos** | Os objetivos são verificáveis, com verbo de ação? |
| **Utilidade prática** | O operador usaria isso como ponto de partida real? |

Meta inicial: média ≥ 3,5 em cada critério; **nenhum** critério abaixo de 3,0.

### Consistência (RNF03)

| Métrica | Como se calcula | Meta |
|---|---|---|
| **Estabilidade** | Mesma entrada, 3 execuções: proporção de campos com valor idêntico nas três. | ≥ 90% nos campos extraídos |
| **Conformidade de schema** | Proporção de respostas válidas **na primeira tentativa**. | ≥ 95% |

### Operação (RNF06, RNF12)

| Métrica | Meta |
|---|---|
| Latência p50 / p95 ponta a ponta | p95 ≤ 15 s (RNF06) |
| Tokens por demanda (entrada + saída) | Base do cálculo de custo |
| Custo por demanda | Ver [custos de operação](custos-operacao.md) |
| Taxa de falha | ≤ 5% das execuções |

### Indicador prático: quanto o humano corrigiu

Aproveitando que `artifact_versions.origem` distingue `IA` de `HUMANO`, é possível medir em produção
a proporção de campos alterados pelo operador entre a versão gerada e a versão aprovada.

É a métrica mais honesta do conjunto: mede utilidade real, não concordância com gabarito de
laboratório. Não substitui as anteriores — complementa, e só existe depois que a plataforma estiver
em uso.

## Como reportar

Relatório por rodada de avaliação, versionado neste diretório:

```
docs/04-ia/avaliacoes/YYYY-MM-DD-<versao-do-prompt>.md
```

Cada relatório traz: versão de prompt, modelo, tamanho do conjunto, tabela de métricas, comparação
com a rodada anterior e conclusão sobre o que mudar.

## Cronograma

| Quando | O quê |
|---|---|
| Até 15/09 | Métricas e critérios de comparação definidos (Fase 2). |
| Até 06/10 | Conjunto com 20 casos anotados. |
| 06–17/10 | Primeira rodada completa de medição. |
| 20/10 | **3ª parcial** — métricas reportadas. |
| Até 17/11 | Segunda rodada, após o refino de prompts. |
