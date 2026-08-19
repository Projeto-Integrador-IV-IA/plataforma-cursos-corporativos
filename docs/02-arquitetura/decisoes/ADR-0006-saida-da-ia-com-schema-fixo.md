# ADR-0006 — Saída da IA com schema fixo e validado

- **Status:** Aceita
- **Data:** 2026-08-19
- **Requisitos:** RNF03, RNF04, RF11, RF12, RF14

## Contexto

RNF03 exige prompts estruturados que garantam **saída consistente em formato previsível**, com schema
de saída definido. RNF04 exige métricas de acurácia e consistência mensuráveis — entregável da 3ª
parcial (20/10).

Modelo de linguagem produz texto. Se a saída for texto livre, três coisas quebram: o frontend não
sabe o que renderizar, o `pipeline-service` não sabe o que gravar, e **não há como medir acurácia**,
porque não existe estrutura a comparar com um gabarito.

## Decisão

**A saída da estruturação é um objeto JSON validado contra um JSON Schema versionado**, mantido em
`packages/contracts/schemas/structured-course.schema.json`.

Regras que acompanham a decisão:

1. **Validar sempre.** Resposta que não passa no schema é **falha**, não é aceita como "quase certa".
   O tratamento segue o caminho de erro de RNF05 — a demanda bruta continua registrada e a operação
   pode ser repetida.
2. **Não inventar.** Campo sem base no texto de entrada vai para `campos_ausentes`, nunca é inferido.
   É isso que permite distinguir *erro de extração* de *informação inexistente na entrada* ao calcular
   as métricas de RNF04 — e é o que dá ao operador o que revisar (RF14).
3. **Prompt é artefato versionado.** Vive em arquivo próprio (`extract-requirements.v1.md`), com
   sufixo de versão; mudança gera `v2`, nunca edição no lugar. Sem versão fixa, uma medição não pode
   ser comparada com a anterior.
4. **Registrar a proveniência.** Todo artefato gerado guarda modelo, versão de prompt, tokens e
   latência. Sem isso, nenhum resultado é reproduzível nem auditável (RNF04, RNF09).
5. **Provedor abstrato.** O serviço fala com uma interface de provedor, não com um SDK específico.
   Existe um provedor falso (`LLM_PROVIDER=mock`) para CI e testes, que não gasta chamada paga (RNF12).

## Alternativas consideradas

| Alternativa | Por que não |
|---|---|
| **Saída em texto livre, interpretada depois** | Transfere o problema para um parser frágil e torna RNF04 inviável — não há o que medir de forma objetiva. |
| **Confiar no schema sem validar** | O modelo erra o formato ocasionalmente. Sem validação, o erro chega ao banco e vira dado corrompido. |
| **Preencher campo ausente com valor plausível** | Alucinação disfarçada de completude. Contamina a métrica de acurácia e engana o operador — o oposto do que RF14 pretende. |
| **Prompt embutido no código** | Impossível comparar medições entre versões; toda alteração exigiria caçar strings pelo código. |
| **Ajuste fino de modelo próprio** | Fora do escopo e do orçamento: não há volume de dados anotados nem justificativa de custo (RNF12). |

## Consequências

**Positivas**

- Frontend e banco recebem estrutura previsível (RNF03).
- Acurácia por campo passa a ser calculável contra gabarito humano (RNF04).
- A CI roda sem chave de API e sem custo, com resultado determinístico (RNF12).
- Trocar de provedor de LLM não altera o contrato da saída.

**Negativas**

- Schema fixo é rígido: acrescentar campo é mudança de contrato, com revisão dupla (ver
  [`CODEOWNERS`](../../../.github/CODEOWNERS)).
- Validar e possivelmente repetir a chamada consome mais tempo e tokens, pressionando o alvo de
  RNF06 (≤ 15 s) e o custo por demanda.
- Manter o conjunto de avaliação anotado dá trabalho humano recorrente. É o preço de ter RNF04
  verificável — e sem ele a 3ª parcial não tem entregável.
