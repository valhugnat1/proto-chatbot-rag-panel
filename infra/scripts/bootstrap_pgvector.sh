#!/usr/bin/env bash
###############################################################################
# bootstrap_pgvector.sh
#
# Active l'extension `pgvector` dans la Serverless SQL Database après le
# `terraform apply` initial. À exécuter UNE SEULE FOIS par database.
#
# Prérequis :
#   - terraform apply a déjà tourné (les outputs sont disponibles)
#   - psql installé localement (`brew install postgresql` sur macOS)
#
# Usage :
#   cd infra/scripts
#   ./bootstrap_pgvector.sh
#
# Pourquoi un script séparé et pas un null_resource Terraform ?
#   - Plus simple à debugger : on voit immédiatement l'erreur psql
#   - Pas de dépendance Terraform sur psql installé sur la machine qui apply
#   - Idempotent : `CREATE EXTENSION IF NOT EXISTS` ne fait rien si déjà actif
###############################################################################

set -euo pipefail

GREEN=$'\033[0;32m'
RED=$'\033[0;31m'
BLUE=$'\033[0;34m'
NC=$'\033[0m'

log() { echo "${BLUE}▶${NC} $*"; }
ok()  { echo "${GREEN}✓${NC} $*"; }
err() { echo "${RED}✗${NC} $*" >&2; }

REPO_ROOT="$(cd "$(dirname "$0")/../.." && pwd)"
TERRAFORM_DIR="$REPO_ROOT/infra/terraform"

if ! command -v psql >/dev/null 2>&1; then
  err "psql non trouvé. Installer postgresql client (brew install postgresql)."
  exit 1
fi

if ! command -v terraform >/dev/null 2>&1; then
  err "terraform non trouvé."
  exit 1
fi

cd "$TERRAFORM_DIR"

log "Lecture des outputs Terraform…"
DB_HOST=$(terraform output -raw db_host)
DB_NAME=$(terraform output -raw db_name)
DB_USER=$(terraform output -raw db_user)
DB_PASSWORD=$(terraform output -raw db_password)
ok "Outputs récupérés (host=$DB_HOST, db=$DB_NAME)"

log "Activation de l'extension pgvector…"
PGPASSWORD="$DB_PASSWORD" psql \
  "host=$DB_HOST port=5432 dbname=$DB_NAME user=$DB_USER sslmode=require" \
  -c "CREATE EXTENSION IF NOT EXISTS vector;"

ok "Extension pgvector activée"

log "Vérification…"
PGPASSWORD="$DB_PASSWORD" psql \
  "host=$DB_HOST port=5432 dbname=$DB_NAME user=$DB_USER sslmode=require" \
  -c "SELECT extname, extversion FROM pg_extension WHERE extname = 'vector';"

echo
echo "${GREEN}════════════════════════════════════════════════════════════════════${NC}"
echo "${GREEN}✅  pgvector activé sur $DB_NAME${NC}"
echo "${GREEN}════════════════════════════════════════════════════════════════════${NC}"
echo
echo "Étape suivante : indexer la base de connaissances."
echo
echo "    export DATABASE_URL=\$(terraform output -raw database_url)"
echo "    export MISTRAL_API_KEY=..."
echo "    cd ../../backend"
echo "    python -m app.rag.ingest all --max-pages 50 --max-depth 2"
echo
