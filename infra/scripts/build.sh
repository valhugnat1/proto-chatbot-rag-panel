#!/usr/bin/env bash
# Usage: build.sh <registry> <tag> <backend_url>
set -euo pipefail

REGISTRY=$1
TAG=$2
BACKEND_URL=$3
REPO_ROOT="$(cd "$(dirname "$0")/../.." && pwd)"

echo "$SCW_SECRET_KEY" | docker login "$REGISTRY" -u nologin --password-stdin

docker buildx inspect bnp-builder >/dev/null 2>&1 || docker buildx create --name bnp-builder --use
docker buildx use bnp-builder

docker buildx build --platform linux/amd64 --push \
  -t "$REGISTRY/backend:$TAG" "$REPO_ROOT/backend"

docker buildx build --platform linux/amd64 --push \
  --build-arg "VITE_API_URL=$BACKEND_URL" \
  -t "$REGISTRY/frontend:$TAG" "$REPO_ROOT/frontend"
