-- Executado apenas na primeira criacao do volume do PostgreSQL.
-- Limitado a preparacao do banco: extensoes e configuracoes de instancia.
-- O SCHEMA DA APLICACAO NAO VEM DAQUI - ele e criado exclusivamente por
-- migrations do Alembic (services/pipeline-service), para que toda mudanca de
-- estrutura fique versionada e auditavel (RNF14 do Documento Consolidado v1.0).

-- Geracao de UUID no banco.
CREATE EXTENSION IF NOT EXISTS "pgcrypto";

-- Busca textual sem acento em nomes de cliente (RF03).
CREATE EXTENSION IF NOT EXISTS "unaccent";
