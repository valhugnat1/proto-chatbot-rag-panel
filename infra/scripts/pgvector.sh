#!/usr/bin/env bash
# Enables the pgvector extension on the prod DB. Run once.
set -euo pipefail

cd "$(dirname "$0")/../terraform"

PGPASSWORD=$(terraform output -raw db_password) psql \
  "host=$(terraform output -raw db_host) port=5432 \
   dbname=$(terraform output -raw db_name) \
   user=$(terraform output -raw db_user) sslmode=require" \
  -c "CREATE EXTENSION IF NOT EXISTS vector;"
