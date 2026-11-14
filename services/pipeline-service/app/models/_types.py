"""Tipos SQL compartilhados pelos modelos relacionais."""

import sqlalchemy as sa
from pgvector.sqlalchemy import Vector
from sqlalchemy.dialects import postgresql

UUID_TYPE = sa.Uuid().with_variant(postgresql.UUID(as_uuid=True), "postgresql")
JSON_TYPE = sa.JSON().with_variant(postgresql.JSONB(), "postgresql")

#: Dimensao fixa do embedding de trecho (RNF28 consolidado, ADR-0007): a do
#: modelo local escolhido para o card #160 (`sentence-transformers/all-MiniLM-L6-v2`
#: via `fastembed`). Trocar de modelo com dimensao diferente exige nova migration.
EMBEDDING_DIMENSION = 384

#: ``vector`` de verdade no Postgres (pgvector); lista JSON em qualquer outro
#: dialeto - o unico outro dialeto deste projeto e o SQLite dos testes, que
#: nao tem tipo vetorial. A leitura devolve ``list[float]`` nos dois casos
#: (pgvector decodifica para lista quando numpy nao esta instalado, e este
#: servico nao depende de numpy), entao o codigo da aplicacao nunca precisa
#: saber qual dialeto esta por tras.
VECTOR_TYPE = sa.JSON().with_variant(Vector(EMBEDDING_DIMENSION), "postgresql")
