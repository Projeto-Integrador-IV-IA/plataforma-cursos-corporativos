# Glossário

Vocabulário comum do projeto e o mapeamento entre os termos do negócio (em português) e os
identificadores usados no código (em inglês).

## Termos de negócio

| Termo | Definição |
|---|---|
| **Cliente** | Empresa que contrata o treinamento. Não confundir com o usuário da plataforma. |
| **Operador** | Profissional que usa a plataforma — hoje, a pessoa que centraliza todo o processo. É o usuário direto do sistema. |
| **Demanda / Negociação** | Uma oportunidade de curso vinculada a um cliente. Percorre o pipeline do início ao fim. |
| **Demanda bruta** | O texto heterogêneo como chegou: e-mail colado, transcrição de reunião, mensagens. Nunca é alterado. |
| **Pipeline** | A sequência de etapas percorrida por uma negociação. |
| **Etapa** | Posição atual da negociação no pipeline: captação, estruturação, produto, proposta, acompanhamento. |
| **Retrocesso** | Voltar a uma etapa anterior porque o cliente mudou escopo ou proposta. É comportamento esperado, não exceção (RF06). |
| **Artefato** | Qualquer documento atrelado à negociação: requisitos extraídos, ementa, proposta. |
| **Versão de artefato** | Estado do artefato em um momento. Nunca é sobrescrita — editar cria versão nova (RF08). |
| **Curso estruturado** | A saída da IA: tema, nicho, público, participantes, carga horária, formato, objetivos e ementa. |
| **Ementa** | Conteúdo programático organizado em módulos, com objetivos de aprendizagem. |
| **Fonte única de verdade** | Princípio central do MVP: tudo de uma negociação existe em um lugar só, versionado e recuperável (RF15). |

## Mapeamento negócio → código

| Português (negócio) | Inglês (código) |
|---|---|
| Cliente | `Client` |
| Demanda / negociação | `Demand` |
| Demanda bruta | `RawInput` |
| Etapa do pipeline | `PipelineStage` |
| Transição de etapa | `StageTransition` |
| Artefato | `Artifact` |
| Versão de artefato | `ArtifactVersion` |
| Curso estruturado | `StructuredCourse` |
| Usuário / operador | `User` |

## Etapas do pipeline

| Etapa (negócio) | Código | Significado |
|---|---|---|
| Captação | `CAPTACAO` | Demanda registrada, ainda bruta. |
| Estruturação | `ESTRUTURACAO` | Demanda enviada à camada de IA ou retornando dela. |
| Produto | `PRODUTO` | Curso estruturado já revisado pelo operador. |
| Proposta | `PROPOSTA` | Proposta montada para o cliente. |
| Acompanhamento | `ACOMPANHAMENTO` | Pós-proposta, negociação em andamento. |

## Termos técnicos

| Termo | Definição |
|---|---|
| **LLM** | *Large Language Model*. O modelo de linguagem que faz a estruturação. |
| **Prompt** | Instrução enviada ao LLM. Aqui é artefato versionado, não string solta no código. |
| **Schema de saída** | Formato fixo que a resposta do LLM precisa respeitar (RNF03). |
| **Append-only** | Tabela que só aceita inserção. Base da trilha de auditoria (RNF09). |
| **ADR** | *Architecture Decision Record*. Registro de uma decisão de arquitetura, seu contexto e suas consequências. |
| **Gateway / BFF** | Porta de entrada única entre o frontend e os serviços internos. |
| **MVP** | *Minimum Viable Product*. O escopo entregue até 17/11. |
