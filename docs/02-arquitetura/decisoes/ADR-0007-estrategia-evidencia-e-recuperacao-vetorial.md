# ADR-0007: Estratégia de Evidência por Trecho Citável e Recuperação Vetorial (pgvector)

## Status
- **Data:** Setembro de 2026
- **Status:** Aceito

## Contexto
O sistema precisa processar textos heterogêneos e extrair requisitos e ementas estruturadas de forma confiável utilizando modelos de linguagem. Para mitigar o risco de alucinações e atender às exigências de auditoria da banca, cada afirmação ou dado estruturado gerado pela IA deve estar estritamente vinculado a **trechos citáveis originais** extraídos das fontes brutas de demanda (`raw-inputs`). 

Além disso, faz-se necessário definir o mecanismo de armazenamento e busca semântica dos vetores (*embeddings*), ponderando a complexidade operacional, a integridade transacional e as restrições de infraestrutura do MVP.

## Decisão
1. **Evidência por Trecho Citável (Citation by Snippet):** A IA retornará identificadores de fonte e os trechos textuais exatos utilizados na geração dos artefatos. Isso viabiliza a exibição visual de comprovação ao operador humano na interface.
2. **Adoção do `pgvector` no PostgreSQL:** Optou-se por utilizar a extensão `pgvector` diretamente no banco relacional já adotado pelos microsserviços do projeto, descartando bancos vetoriais dedicados externos.
3. **Alinhamento com ADR-0004 e ADR-0006:** A decisão complementa a arquitetura de persistência unificada (ADR-0004) e respeita o esquema fixo de saída estruturada estabelecido na ADR-0006.

## Alternativas Consideradas e Descartadas
- **Banco Vetorial Dedicado (ex: Qdrant, Milvus ou Pinecone):** Descartado para o MVP devido à sobrecarga de manutenção de uma nova infraestrutura distribuída, complexidade de gerenciamento no Docker Compose e ausência de volumetria que justifique múltiplos storages.
- **Busca puramente baseada em Full-Text Search convencional:** Descartada por não abranger similaridade semântica profunda sobre entradas informais de linguagem natural (como transcrições de reuniões e áudios).

## Consequências
- **Positivas:** 
  - Arquitetura enxuta e unificada (um único banco relacional gerencia dados relacionais e vetoriais).
  - Integridade referencial garantida por chaves estrangeiras entre artefatos e trechos brutos.
  - Atendimento estrito aos critérios de rastreabilidade exigidos pelo requisito RF29.
- **Negativas / Trade-offs:** 
  - Escalabilidade de busca vetorial limitada ao limite de desempenho do PostgreSQL em instâncias únicas (suficiente e adequado para o escopo do MVP corporativo atual).