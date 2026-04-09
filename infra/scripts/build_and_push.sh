#!/usr/bin/env bash
###############################################################################
# build_and_push.sh
#
# Build et push des images Docker `backend` et `frontend` vers le Container
# Registry Scaleway, depuis un Mac M3 (ARM) vers du linux/amd64 (Scaleway).
#
# Usage typique :
#
#   # 1. Premier déploiement : créer registry + DB d'abord
#   cd ../terraform
#   terraform init
#   terraform apply -target=scaleway_container_namespace.main \
#                   -target=scaleway_sdb_sql_database.bnp \
#                   -target=scaleway_iam_application.backend \
#                   -target=scaleway_iam_api_key.backend
#
#   # 2. Récupérer l'endpoint registry et l'URL backend (placeholder)
#   export REGISTRY=$(terraform output -raw registry_endpoint)
#   export BACKEND_URL="https://placeholder-will-be-updated.functions.fnc.fr-par.scw.cloud"
#
#   # 3. Premier build & push (frontend pointera vers le placeholder)
#   cd ../scripts
#   ./build_and_push.sh
#
#   # 4. Premier apply complet
#   cd ../terraform
#   TAG=$(cat /tmp/bnp-image-tag)
#   terraform apply -var "image_tag=$TAG" -var "mistral_api_key=..."
#
#   # 5. Maintenant on a la VRAIE URL backend → rebuild frontend avec
#   export BACKEND_URL=$(terraform output -raw backend_url)
#   cd ../scripts
#   ./build_and_push.sh
#
#   # 6. Re-apply pour déployer le nouveau frontend
#   cd ../terraform
#   TAG=$(cat /tmp/bnp-image-tag)
#   terraform apply -var "image_tag=$TAG" -var "mistral_api_key=..."
#
# Itérations suivantes : juste les étapes 5+6.
###############################################################################

set -euo pipefail

# --- Couleurs pour la lisibilité ---
RED=$'\033[0;31m'
GREEN=$'\033[0;32m'
YELLOW=$'\033[0;33m'
BLUE=$'\033[0;34m'
NC=$'\033[0m'

log()  { echo "${BLUE}▶${NC} $*"; }
ok()   { echo "${GREEN}✓${NC} $*"; }
warn() { echo "${YELLOW}⚠${NC} $*"; }
err()  { echo "${RED}✗${NC} $*" >&2; }

# --- Configuration ---
# Le registry endpoint vient soit de l'env (recommandé), soit on essaie de
# l'extraire via terraform output.
REPO_ROOT="$(cd "$(dirname "$0")/../.." && pwd)"
TERRAFORM_DIR="$REPO_ROOT/infra/terraform"

if [[ -z "${REGISTRY:-}" ]]; then
  log "REGISTRY non défini, lecture depuis terraform output…"
  if ! REGISTRY=$(cd "$TERRAFORM_DIR" && terraform output -raw registry_endpoint 2>/dev/null); then
    err "Impossible de lire REGISTRY. Faire un premier 'terraform apply' d'abord, ou exporter REGISTRY=rg.fr-par.scw.cloud/<namespace>"
    exit 1
  fi
fi

if [[ -z "${BACKEND_URL:-}" ]]; then
  warn "BACKEND_URL non défini, le frontend sera buildé avec http://localhost:8000"
  warn "→ ce build n'est utilisable QUE pour un test local"
  BACKEND_URL="http://localhost:8000"
fi

# Tag = timestamp si non fourni
TAG="${1:-$(date +%Y%m%d-%H%M%S)}"
PLATFORM="linux/amd64"

# Sanity check sur les credentials
if [[ -z "${SCW_SECRET_KEY:-}" ]]; then
  err "SCW_SECRET_KEY non défini dans l'environnement"
  exit 1
fi

log "Configuration :"
echo "    Registry  : $REGISTRY"
echo "    Tag       : $TAG"
echo "    Platform  : $PLATFORM"
echo "    Backend   : $BACKEND_URL (baked into frontend)"
echo

# --- Login au registry Scaleway ---
log "Login au Container Registry Scaleway…"
echo "$SCW_SECRET_KEY" | docker login "$REGISTRY" -u nologin --password-stdin
ok "Login réussi"

# --- Buildx builder ---
if ! docker buildx inspect bnp-builder >/dev/null 2>&1; then
  log "Création du builder buildx 'bnp-builder'…"
  docker buildx create --name bnp-builder --use
else
  docker buildx use bnp-builder
fi
ok "Builder buildx prêt"

# --- Build & push backend ---
log "Build & push backend ($PLATFORM)…"
docker buildx build \
  --platform "$PLATFORM" \
  --tag "$REGISTRY/backend:$TAG" \
  --tag "$REGISTRY/backend:latest" \
  --push \
  "$REPO_ROOT/backend"
ok "Backend pushé : $REGISTRY/backend:$TAG"

# --- Build & push frontend ---
log "Build & push frontend ($PLATFORM)…"
docker buildx build \
  --platform "$PLATFORM" \
  --build-arg "VITE_API_URL=$BACKEND_URL" \
  --tag "$REGISTRY/frontend:$TAG" \
  --tag "$REGISTRY/frontend:latest" \
  --push \
  "$REPO_ROOT/frontend"
ok "Frontend pushé : $REGISTRY/frontend:$TAG"

# --- Persiste le tag pour terraform ---
echo "$TAG" > /tmp/bnp-image-tag
ok "Tag sauvé dans /tmp/bnp-image-tag"

echo
echo "${GREEN}════════════════════════════════════════════════════════════════════${NC}"
echo "${GREEN}✅  Build & push terminé !${NC}"
echo "${GREEN}════════════════════════════════════════════════════════════════════${NC}"
echo
echo "Tag d'image : ${YELLOW}$TAG${NC}"
echo
echo "Prochaine étape :"
echo "    cd $TERRAFORM_DIR"
echo "    terraform apply -var \"image_tag=$TAG\""
echo
