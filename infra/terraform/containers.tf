###############################################################################
# containers.tf
#
# Deux Serverless Containers :
#   - backend  : FastAPI + LangGraph, min_scale = 1 (pas de cold start)
#   - frontend : nginx servant le build Vue, min_scale = 0 (peut dormir)
#
# Les images sont buildées et poussées par `infra/scripts/build_and_push.sh`
# AVANT chaque `terraform apply`. Le tag d'image est passé via la variable
# `image_tag` (timestamp) pour forcer le redéploiement.
#
# Couplage chicken-and-egg : le frontend a besoin de l'URL du backend au build
# time (env Vite). On résout ça en deux étapes :
#   1. premier `apply` (sans frontend ou avec image placeholder) → URL backend
#   2. build_and_push.sh avec BACKEND_URL exporté → image frontend correcte
#   3. second `apply` avec le nouveau tag
# Voir le README pour la procédure complète.
###############################################################################

# Tag d'image courant — on récupère l'endpoint du registry depuis le namespace
# pour construire les références d'image complètes.
locals {
  registry        = scaleway_container_namespace.main.registry_endpoint
  backend_image   = "${local.registry}/backend:${var.image_tag}"
  frontend_image  = "${local.registry}/frontend:${var.image_tag}"
}

###############################################################################
# Backend
###############################################################################

resource "scaleway_container" "backend" {
  name         = "${var.project_name}-${var.environment}-backend"
  description  = "FastAPI + LangGraph ReAct agent (Mistral + pgvector)"
  namespace_id = scaleway_container_namespace.main.id

  registry_image = local.backend_image
  port           = 8000
  protocol       = "http1"

  # Sizing — 1 vCPU / 2 GB suffisent largement pour le POC.
  cpu_limit    = 1000 # millicores → 1 vCPU
  memory_limit = 2048 # MB

  # min_scale = 1 → pas de cold start au premier message du démo.
  # Coût : ~5 €/mois au repos, mais l'expérience utilisateur est nette.
  min_scale       = 1
  max_scale       = 3
  max_concurrency = 20
  timeout         = 300 # 5 min, pour absorber les générations LangGraph longues

  privacy     = "public"
  http_option = "redirected" # force HTTPS

  # Variables non sensibles
  environment_variables = {
    MISTRAL_MODEL       = var.mistral_model
    MISTRAL_EMBED_MODEL = var.mistral_embed_model
    FRONTEND_URL        = "https://${scaleway_container.frontend.domain_name}"
    LOG_LEVEL           = "INFO"
  }

  # Variables sensibles (chiffrées au repos par Scaleway)
  secret_environment_variables = {
    MISTRAL_API_KEY = var.mistral_api_key
    DATABASE_URL    = local.database_url
  }

  deploy = true

  # Le backend dépend de la DB (pour le DSN) et du registry (pour l'image).
  depends_on = [
    scaleway_sdb_sql_database.bnp,
    scaleway_iam_api_key.backend,
  ]
}

###############################################################################
# Frontend
###############################################################################

resource "scaleway_container" "frontend" {
  name         = "${var.project_name}-${var.environment}-frontend"
  description  = "Vue 3 SPA servie par nginx"
  namespace_id = scaleway_container_namespace.main.id

  registry_image = local.frontend_image
  port           = 80
  protocol       = "http1"

  # nginx servant des fichiers statiques → on peut être très petit.
  cpu_limit    = 500 # 0.5 vCPU
  memory_limit = 512 # MB

  # Le frontend peut dormir : c'est juste du nginx, le cold start est ~1 s.
  min_scale       = 0
  max_scale       = 2
  max_concurrency = 80
  timeout         = 60

  privacy     = "public"
  http_option = "redirected"

  deploy = true
}
