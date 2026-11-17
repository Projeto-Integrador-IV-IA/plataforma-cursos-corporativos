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

## Nota de implementação (cards #158/#159, novembro de 2026)

A extensão `vector` foi habilitada (imagem `pgvector/pgvector:pg16` no Compose, `CREATE EXTENSION` no init script e na migration) e o armazenamento foi modelado em `segment_embeddings`, com chave composta `(segment_id, model)` — append-only, igual ao restante do projeto (RNF09): trocar de modelo de embedding soma uma linha nova em vez de substituir a existente. Um índice `hnsw (vector_cosine_ops)` foi criado para uso futuro.

**Desvio consciente desta ADR:** a busca por similaridade em si (`SegmentEmbeddingRepository.search_similar`) calcula a similaridade de cosseno em **Python**, não pelo operador nativo `<=>` do pgvector. Motivo: a suíte de testes deste serviço roda inteiramente contra SQLite (nenhum serviço de Postgres sobe no CI hoje), que não tem tipo vetorial nem operador de distância — um caminho de busca escrito só para o dialeto Postgres nunca seria exercitado pela suíte, divergindo do que é testado do que roda em produção. No volume de um MVP (poucos trechos por demanda), a comparação em Python sobre o conjunto já filtrado por demanda é imediata. O índice `hnsw` fica pronto para quando o volume justificar trocar este cálculo por uma consulta nativa — e, nesse momento, caberá também provisionar Postgres no CI para testar o caminho de verdade.

## Nota de implementação (cards #160/#161/#162, novembro de 2026)

O lado que gera e consome os vetores (`ai-structuring-service`) foi implementado espelhando o padrão de `LLMProvider` (RNF03): `EmbeddingProvider` é a abstração, com `MockEmbeddingProvider` (vetor determinístico por hash, sem rede — o único usado na CI) e `FastEmbedProvider` (modelo local `sentence-transformers/all-MiniLM-L6-v2` em ONNX, via `fastembed`, baixado uma vez e depois totalmente offline) como implementações concretas, selecionadas por `EMBEDDING_PROVIDER`. A dimensão (384) é a mesma `EMBEDDING_DIMENSION` já fixada em `pipeline-service` (cards #158/#159).

**Card #160** (gerar embeddings): `POST /api/v1/demands/{demand_id}/embeddings` busca os trechos já persistidos pelo pipeline-service (`GET /api/v1/demands/{id}/segments`), gera um vetor por trecho e envia o lote para armazenamento (`POST /api/v1/segment-embeddings`). Demanda sem trecho persistido não é erro — devolve zero trechos embeddados — porque o encadeamento de captação que persiste `source_segments` (RF27, `segment_text()` em `ingestion-service`) ainda não está ligado ao fluxo real de captação; **gap conhecido, fora do escopo destes três cards**, que o `relatório-tecnico.md` também registra.

**Cards #161/#162** (recuperar e limitar o contexto): `StructuringService._montar_trechos` decide, antes de montar o prompt de extração, entre os trechos recuperados por similaridade ou o texto completo (`numerar_trechos`, comportamento de sempre). A recuperação só entra quando `RETRIEVAL_ENABLED=true` *e* a demanda já tem embedding gravado (`search_similar_segments` devolve algum resultado acima de `RETRIEVAL_MIN_SIMILARITY`); qualquer outra condição — flag desligada, provedor/cliente ausentes, nenhum resultado, falha de rede — cai no texto completo, em silêncio, nunca em erro. É exatamente o critério de aceite do #161: "o caminho sem recuperação continua disponível para comparação de qualidade" como padrão seguro, não como modo de emergência.

O corte por tamanho (#162) é por **caracteres** (`RETRIEVAL_MAX_CONTEXT_CHARS`), não por contagem de token do modelo: os resultados já chegam ordenados por similaridade decrescente, e truncar é só parar de acumular trecho quando a soma passaria do teto — descarta sempre os menos relevantes primeiro, nunca reordena. Contagem de token exata depende do tokenizador do modelo em uso (varia por provedor de LLM) e ficaria sempre defasada de qual modelo está configurado; caracteres são uma proxy conservadora e suficiente para o volume do MVP.

**Desvio consciente, pelo mesmo motivo do pgvector acima:** a numeração da citação em `evidencias` (RF28) continua por posição dentro da chamada (`[n] trecho`, 1-indexado), igual a quando a fonte inteira é enviada — trocar a origem do trecho (texto completo vs. recuperado) não troca como ele é citado. O identificador estável do trecho (`segment_id`) que a busca devolve não chega à citação ainda; ligar os dois exigiria revisitar o esquema de `StructuredCourse.evidencias` e as telas que já consomem a numeração por posição (#308, #312), risco maior do que cabia nesta rodada.