# Catálogo de prompts

Prompts são **artefatos versionados**, não strings soltas no código. Cada prompt vive em um arquivo
próprio, com sufixo de versão, e nunca é editado no lugar: mudança gera `v2`.

Por quê: RNF03 exige saída consistente em formato previsível e RNF04 exige métricas de qualidade
comparáveis. Sem versão fixa de prompt, uma medição não pode ser comparada com a anterior.

## Convenção

```
<funcao>.v<N>.md      ex.: extract-requirements.v1.md, generate-syllabus.v1.md
```

Cada arquivo contém, nesta ordem:

1. **Metadados** — versão, data, autor, modelo alvo, o que mudou em relação à versão anterior.
2. **Instrução de sistema** — papel, restrições, política de campo ausente.
3. **Schema de saída** — referência ao JSON Schema em `packages/contracts/schemas/`.
4. **Exemplos** — poucos, reais, anonimizados.

## Prompts previstos

| Arquivo | Função | Requisito |
|---|---|---|
| `extract-requirements.v1.md` | Extrair tema, nicho, público, nº de participantes, carga horária e formato do texto bruto. | RF11 |
| `generate-syllabus.v1.md` | Gerar ementa com objetivos de aprendizagem a partir dos requisitos extraídos. | RF12 |

## Regras

- Nada de dado real de cliente nos exemplos sem anonimização (RNF10).
- Toda alteração de prompt exige nova rodada de avaliação antes do merge (RNF04).
- O prompt em uso é escolhido por configuração, não por edição de código.

> Estado: **conteúdo pendente**. Os prompts são construídos na PoC da Fase 2 (05–15/09).
