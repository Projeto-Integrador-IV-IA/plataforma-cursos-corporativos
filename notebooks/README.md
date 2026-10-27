# Notebooks

Análise que não é código de produção, mas que precisa ser reproduzível e versionada.

## `avaliacao-de-modelos.ipynb`

Compara modelos de linguagem sobre o **mesmo** conjunto de avaliação, medindo o pipeline real do
`ai-structuring-service` — prompt versionado, barreira de schema e política de retentativa
incluídas. Implementa a especificação de [`docs/04-ia/metricas-qualidade.md`](../docs/04-ia/metricas-qualidade.md).

Atende RNF04 e é o entregável de métricas da 3ª parcial. O código de apoio vive no serviço, em
`services/ai-structuring-service/app/evaluation/`, não no notebook: o notebook orquestra e
apresenta, e é testado por `tests/unit/test_evaluation_*.py`.

### Como rodar

```bash
cd services/ai-structuring-service
pip install -e ".[dev,avaliacao]"

cd ../../notebooks
jupyter lab avaliacao-de-modelos.ipynb
```

Sem `OPENROUTER_API_KEY` no ambiente, o notebook roda com o provedor mock e avisa — assim ele
funciona ponta a ponta em qualquer máquina. Para rodar de verdade:

```bash
export OPENROUTER_API_KEY=...        # nunca comitado (RNF11)
```

### O que ele produz

| Saída | Onde |
|---|---|
| Relatório da rodada | `docs/04-ia/avaliacoes/AAAA-MM-DD-<prompt>.md` |
| Saídas brutas do modelo | `docs/04-ia/avaliacoes/dados/AAAA-MM-DD-<prompt>.json` |

As saídas brutas são gravadas **antes** de qualquer métrica ser calculada. Chamada de LLM custa
dinheiro e tempo; reanálise não pode exigir rodada nova.

### Limites que o notebook declara em vez de esconder

- **Cinco dos oito campos não têm acurácia automática.** O critério fixado pelo projeto para
  `tema`, `nicho` e `publico_alvo` é equivalência semântica julgada por dois humanos, e para
  `ementa` e `objetivos_aprendizagem` é escala de 1 a 5. Comparar esses campos por igualdade de
  string daria acurácia artificialmente baixa, então eles ficam fora do número e saem listados
  como pendentes.
- **Métrica não medida sai como `n/d`, nunca como zero.** Conjunto sem campo sem base não tem taxa
  de alucinação, e imprimir 0% afirmaria uma medição que não aconteceu.
- **Custo sai como `n/d` enquanto o preço não for consultado** e datado em
  `app/evaluation/modelos.toml`. Preço zero é sentinela de "não consultado", não de "gratuito".
- **Enquanto o conjunto for sintético, os números validam o arnês, não o produto.** A célula de
  carregamento informa quantos casos reais anonimizados existem, e o relatório gerado carrega o
  aviso no topo.

### Convenções

Notebook é comitado **com as saídas da última execução**, para quem avalia o projeto poder ler o
resultado sem rodar nada. Em troca, nenhuma célula pode conter segredo, caminho absoluto de
máquina pessoal ou dado de cliente não anonimizado.
