# Relatório comparativo e recomendação de modelo de IA (RNF29, card #220)

## 1. Contexto e objetivo

Este relatório consolida duas fontes de dado, nunca misturadas sem identificação clara:

1. **Preço catalogado** dos quatro modelos candidatos originais (Sonnet 4.5, GPT-4o mini, Gemini 2.5
   Flash, Llama 3.3 70B) — consultado direto na API pública do OpenRouter, sem chamada de
   estruturação nova nesta rodada.
2. **Medição real**, nesta rodada, de três modelos da família DeepSeek entre si — a disputa
   interna que este relatório existe para resolver antes de levar DeepSeek à disputa entre
   fornecedores: vale pagar mais pelo raciocínio em cadeia (R1) dentro da própria família, ou o
   nível mais barato (V4.1 Flash) já entrega o que o produto precisa?

O critério que a banca cobra — trade-off entre qualidade, custo e latência, explicitado e
reproduzível — é o que a seção 3 responde para a disputa interna, e a seção 2 declara as condições
exatas para que outra pessoa repita a medição.

## 2. Condições de execução (reprodutibilidade)

| Condição | Valor |
|---|---|
| Data da rodada | 04/11/2026 |
| Provedor | OpenRouter (`LLM_PROVIDER=openrouter`), API real, chave rotacionada após o teste |
| Versão do prompt | `extract-requirements.v6` |
| Versão do schema | registrada em `docs/04-ia/avaliacoes/dados/2026-11-04-v6.json` (`schema_version`) |
| Parâmetros fixos | `temperature=0`, `LLM_TIMEOUT_SECONDS=90`, `LLM_MAX_RETRIES=2`, `LLM_SCHEMA_MAX_RETRIES=2` |
| Caso de uso medido | `StructuringService.structure_course` — o mesmo que `POST /api/v1/structuring` expõe, não uma cópia |
| Conjunto de avaliação | 3 casos **sintéticos** (`tests/fixtures/`) — **0 casos reais anonimizados** |
| Execuções | 3 modelos × 3 casos × 1 repetição = 9 chamadas reais |
| Saída bruta | `docs/04-ia/avaliacoes/dados/2026-11-04-v6.json` — fonte das métricas, não este texto |
| Repositório do catálogo de preço | `services/ai-structuring-service/app/evaluation/modelos.toml` |

**Limite que nenhum número abaixo esconde:** o conjunto de avaliação não tem caso real anotado por
humano (RNF07.2/#18, ainda bloqueado por falta de dado real anonimizado do cliente). As métricas de
qualidade desta rodada validam que o arnês de avaliação funciona — não são medição reportável da
qualidade do produto. Isso é declarado porque é o critério do próprio `metricas-qualidade.md`, não
uma ressalva adicionada depois.

**Bug de produção encontrado e corrigido durante esta rodada:** `app/evaluation/runner.py` reusava o
mesmo objeto `Settings` para todos os modelos da rodada. Como `CompletionParams.model` vem de
`self._settings.llm_model`, e esse campo nunca era sobrescrito por modelo dentro do laço, **toda
chamada contra um provedor HTTP real pedia sempre o mesmo modelo**, não importa qual candidato o
catálogo indicasse — mascarado até hoje porque o provedor mock ignora esse campo (recebe o `model`
direto no construtor). Esta é a primeira rodada deste projeto com múltiplos modelos reais no mesmo
lote contra um provedor HTTP, e por isso a primeira a expor o defeito. Corrigido com um
`config.model_copy(update={"llm_model": modelo.slug})` por modelo, dentro do laço; confirmado pelo
provedor devolvendo `modelo_reportado` igual ao `modelo` pedido nas 9 execuções desta rodada (antes
da correção, 6 das 9 foram servidas pelo modelo errado). Suíte completa (359 testes) permanece verde
após a correção.

## 3. Disputa interna DeepSeek — medição real

| Modelo | Tokens entrada (méd.) | Tokens saída (méd.) | Latência p50 | Latência p95 | Custo/demanda (USD) | Conformidade de schema |
|---|--:|--:|--:|--:|--:|--:|
| DeepSeek R1 (reasoning) | 7 064 | 2 027 | 45,5 s | 147,3 s | $0,007890 | 100% |
| DeepSeek Chat V3.1 | 7 063 | 289 | 11,6 s | 12,8 s | $0,002041 | 100% |
| DeepSeek V4.1 Flash | 7 089 | 3 158 | 8,6 s | 25,0 s | $0,001898 | 100% |

Acurácia automática (`numero_participantes`, `carga_horaria`, `formato`), cobertura, alucinação,
reconhecimento de ausência, evidência e taxa de citação inválida saíram **idênticas entre os três
modelos** (33% / 45% / 0% / 25% / 100% / 0%) — ver `2026-11-04-v6.md`. Com apenas 3 casos sintéticos,
essa igualdade não diz que os modelos têm a mesma qualidade: diz que o conjunto atual não tem
variação suficiente para diferenciá-los nessas métricas. A diferenciação real desta rodada está em
custo e latência, não em qualidade automática — e fica assim até o conjunto ter os 20 casos reais
anotados que a 3ª parcial pede.

**O que os números acima mostram, com confiança:**

- **R1 é o único com raciocínio em cadeia**, e isso custa caro nos dois eixos que importam para este
  produto: 4–6× mais tokens de saída que os outros dois, e latência p95 de quase 2,5 minutos — muito
  acima do alvo de 15 s do RNF06. Para uma tarefa de extração estruturada com schema fixo, que não
  pede argumentação em várias etapas, o raciocínio extra não tem onde se gastar de forma útil.
- **V4.1 Flash, apesar do nome, não foi o mais econômico em tokens** — produziu mais tokens de saída
  em média que o Chat V3.1 (3 158 vs. 289) e teve a cauda de latência mais instável (8,6 s a 25 s).
  Ainda assim ficou mais barato por demanda porque seu preço por token de saída é a fração do dos
  outros dois ($0,50/Mtok contra $0,95 e $2,15).
  Vale levantar: dado o `supported_parameters` do modelo incluir `reasoning`/`include_reasoning`,
  parte dessa saída maior pode ser raciocínio implícito não solicitado — não investigado nesta
  rodada, fica como item de acompanhamento antes de adotar o modelo em produção.
- **Chat V3.1 é o mais previsível**: saída enxuta (289 tokens, baixa variância entre casos), latência
  estável (11,6 a 13,0 s, a menor variação dos três) e custo intermediário.

## 4. Recomendação e justificativa do trade-off

**Modelo recomendado para a disputa interna DeepSeek: `deepseek/deepseek-chat-v3.1`.**

Não é o mais barato por demanda nesta amostra pequena ($0,002041 contra $0,001898 do V4.1 Flash) —
mas a diferença é de $0,000143 por demanda, irrelevante no volume do cliente (seção 5), enquanto a
previsibilidade de latência e de tamanho de saída do Chat V3.1 pesa mais para um produto com alvo de
resposta em até 15 s (RNF06). R1 fica descartado para este fluxo: o custo de raciocínio em cadeia
não se paga numa tarefa de extração com schema fixo, e sua latência p95 viola o alvo de tempo por
uma margem grande. V4.1 Flash permanece candidato de reserva para cenários onde custo marginal
importa mais que previsibilidade de latência, condicionado a investigar a saída maior que a
observada no Chat V3.1.

**Frente aos quatro candidatos originais do catálogo** (preço, não medição nova desta rodada): o
Chat V3.1 ($0,25/$0,95 por Mtok) fica abaixo do GPT-4o mini ($0,15/$0,60 só na entrada, mais caro na
saída) e muito abaixo do Sonnet 4.5 ($3,00/$15,00) e do Gemini 2.5 Flash ($0,30/$2,50) na saída, que
é o lado mais caro desta tarefa (saída inclui o JSON estruturado inteiro). Uma rodada de qualidade
cruzando DeepSeek Chat V3.1 contra os quatro candidatos originais, no mesmo conjunto, é o próximo
passo natural — e só vira número reportável quando o conjunto tiver os casos reais anotados (seção
2).

## 5. Custo projetado

Ver a planilha preenchida em [`custos-operacao.md`](../custos-operacao.md#planilha-preenchida-na-3-parcial).
Resumo: no volume do cliente (2–3 demandas/dia), o custo mensal de API para qualquer um dos três
candidatos DeepSeek fica abaixo de US$ 0,60/mês — a extração é hoje a única chamada medida; o passo
de geração de ementa (RF12) ainda não existe como chamada separada (`generate-syllabus.v1` continua
rascunho), então o custo real de produção, quando esse passo existir, será maior que o medido aqui.

## 6. Saídas brutas e rastreabilidade

- Dados brutos desta rodada: [`dados/2026-11-04-v6.json`](dados/2026-11-04-v6.json)
- Relatório automático da rodada (template de `avaliacoes/README.md`): [`2026-11-04-v6.md`](2026-11-04-v6.md)
- Catálogo com os três modelos DeepSeek e preço datado: `services/ai-structuring-service/app/evaluation/modelos.toml`
- Correção de bug aplicada: `services/ai-structuring-service/app/evaluation/runner.py`
