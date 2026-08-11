-- Extensões e o banco de teste. Roda uma vez, na criação do volume.
CREATE EXTENSION IF NOT EXISTS citext;
CREATE EXTENSION IF NOT EXISTS pg_trgm;

CREATE DATABASE assessoria_test OWNER assessoria;
\connect assessoria_test
CREATE EXTENSION IF NOT EXISTS citext;
CREATE EXTENSION IF NOT EXISTS pg_trgm;
