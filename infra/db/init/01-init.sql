-- Executado apenas na primeira criacao do volume do PostgreSQL.
-- Limitado a preparacao do banco: extensoes e configuracoes de instancia.
-- O SCHEMA DA APLICACAO NAO VEM DAQUI - ele e criado exclusivamente por
-- migrations do Alembic (services/pipeline-service), para que toda mudanca de
-- estrutura fique versionada e auditavel (RNF08, RNF09).

-- Geracao de UUID no banco.
CREATE EXTENSION IF NOT EXISTS "pgcrypto";

-- Busca textual sem acento em nomes de cliente (RF03).
CREATE EXTENSION IF NOT EXISTS "unaccent";

-- Tipo de vetor e indice de similaridade para embeddings de trecho (RNF28
-- consolidado, ADR-0007). Tambem habilitada na migration (card #158): esta
-- linha cobre a imagem provisionada do zero por este script; a migration
-- cobre quem roda "alembic upgrade head" direto contra um Postgres que nunca
-- viu este diretorio de init (ex.: banco de teste criado fora do Compose).
CREATE EXTENSION IF NOT EXISTS "vector";
