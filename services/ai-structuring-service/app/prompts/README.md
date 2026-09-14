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
| `extract-requirements.v1.md` | Extrair os cinco campos pedagógicos — tema, público-alvo, carga horária, ementa e objetivos de aprendizagem — do texto normalizado. **Escrito** (card #5). | RF13 (RF11 na matriz) |
| `generate-syllabus.v1.md` | Gerar ementa com objetivos de aprendizagem a partir dos requisitos extraídos. | RF12 |

## Regras

- Nada de dado real de cliente nos exemplos sem anonimização (RNF10).
- Toda alteração de prompt exige nova rodada de avaliação antes do merge (RNF04).
- O prompt em uso é escolhido por configuração, não por edição de código.

## Como carregar

O prompt é lido do arquivo pelo nome e pela versão — nunca embutido como string no serviço:

```python
from app.prompts import carregar_prompt

prompt = carregar_prompt("extract-requirements", "v1")
texto = prompt.render(texto_normalizado=demanda)
```

As variáveis do corpo usam chaves duplas (`{{texto_normalizado}}`), porque o corpo tem exemplos em
JSON e chave simples colidiria com eles. `render()` falha se faltar variável ou se vier variável que
o prompt não usa — prompt e chamador fora de sincronia é defeito, não detalhe. `prompt.identificador`
(`extract-requirements.v1`) é o que vai para a proveniência do artefato (RNF04, RNF09).

> Estado: `extract-requirements.v1` **escrito**; `generate-syllabus.v1` pendente, construído na PoC
> da Fase 2 (05–15/09).
