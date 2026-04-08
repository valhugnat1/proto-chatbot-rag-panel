-- Enable pgvector on first database boot.
-- The pgvector/pgvector image ships the extension binaries; we still need
-- to CREATE EXTENSION inside our database.
CREATE EXTENSION IF NOT EXISTS vector;
