# Relatórios de avaliação

Uma rodada de avaliação, um relatório. Nomeie por data e versão de prompt:

```
YYYY-MM-DD-<versao-do-prompt>.md      ex.: 2026-10-08-extract-requirements.v2.md
```

## Modelo de relatório

```markdown
# Avaliação — <versão do prompt> — <data>

## Configuração
- Modelo:
- Versão do prompt:
- Casos avaliados:
- Temperatura:

## Resultados
| Métrica | Valor | Meta | Rodada anterior |
|---|---|---|---|

## Análise
O que melhorou, o que piorou e por quê.

## Erros representativos
2 ou 3 casos concretos que falharam, com o texto de entrada e a saída obtida.

## Decisão
O que muda no prompt, no modelo ou no schema para a próxima rodada.
```

Critérios e metas em [metricas-qualidade.md](../metricas-qualidade.md).

> Nenhuma rodada realizada ainda. A primeira ocorre entre 06 e 17/10, para a 3ª parcial.
