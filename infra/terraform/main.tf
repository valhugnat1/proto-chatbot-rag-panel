terraform {
  required_version = ">= 1.5"
  required_providers {
    scaleway = {
      source  = "scaleway/scaleway"
      version = ">= 2.40"
    }
  }
}

provider "scaleway" {
  region     = "fr-par"
  project_id = var.project_id
}

# --- Variables ---------------------------------------------------------------

variable "project_id" {
  type = string
}

variable "mistral_api_key" {
  type      = string
  sensitive = true
}

variable "image_tag" {
  type    = string
  default = "latest"
}

locals {
  name = "bnp-chatbot"
}

# --- Container registry + namespace ------------------------------------------

resource "scaleway_container_namespace" "main" {
  name       = local.name
  project_id = var.project_id
}

# --- IAM identity for the backend to reach the DB ----------------------------

resource "scaleway_iam_application" "backend" {
  name = "${local.name}-backend"
}

resource "scaleway_iam_policy" "backend_db" {
  name           = "${local.name}-backend-db"
  application_id = scaleway_iam_application.backend.id
  rule {
    project_ids          = [var.project_id]
    permission_set_names = ["ServerlessSQLDatabaseReadWrite"]
  }
}

resource "scaleway_iam_api_key" "backend" {
  application_id = scaleway_iam_application.backend.id
}

# --- Serverless SQL Database (pgvector-capable) ------------------------------

resource "scaleway_sdb_sql_database" "bnp" {
  name       = local.name
  project_id = var.project_id
  min_cpu    = 0
  max_cpu    = 4
}

locals {
  db_host      = regex("postgres://([^:/]+)", scaleway_sdb_sql_database.bnp.endpoint)[0]
  database_url = "postgresql+psycopg://${scaleway_iam_application.backend.id}:${scaleway_iam_api_key.backend.secret_key}@${local.db_host}:5432/${scaleway_sdb_sql_database.bnp.name}?sslmode=require"
}

# --- Backend container (FastAPI + LangGraph) ---------------------------------

resource "scaleway_container" "backend" {
  name           = "${local.name}-backend"
  namespace_id   = scaleway_container_namespace.main.id
  registry_image = "${scaleway_container_namespace.main.registry_endpoint}/backend:${var.image_tag}"
  port           = 8000
  cpu_limit      = 1000
  memory_limit   = 2048
  min_scale      = 1
  max_scale      = 3
  timeout        = 300
  privacy        = "public"
  http_option    = "redirected"
  deploy         = true

  environment_variables = {
    MISTRAL_MODEL       = "mistral-large-latest"
    MISTRAL_EMBED_MODEL = "mistral-embed"
    FRONTEND_URL        = "https://${scaleway_container.frontend.domain_name}"
  }

  secret_environment_variables = {
    MISTRAL_API_KEY = var.mistral_api_key
    DATABASE_URL    = local.database_url
  }
}

# --- Frontend container (Vue SPA on nginx) -----------------------------------

resource "scaleway_container" "frontend" {
  name           = "${local.name}-frontend"
  namespace_id   = scaleway_container_namespace.main.id
  registry_image = "${scaleway_container_namespace.main.registry_endpoint}/frontend:${var.image_tag}"
  port           = 80
  cpu_limit      = 500
  memory_limit   = 512
  min_scale      = 0
  max_scale      = 2
  timeout        = 60
  privacy        = "public"
  http_option    = "redirected"
  deploy         = true
}

# --- Outputs -----------------------------------------------------------------

output "frontend_url" {
  value = "https://${scaleway_container.frontend.domain_name}"
}

output "backend_url" {
  value = "https://${scaleway_container.backend.domain_name}"
}

output "registry_endpoint" {
  value = scaleway_container_namespace.main.registry_endpoint
}

output "db_host" {
  value = local.db_host
}

output "db_name" {
  value = scaleway_sdb_sql_database.bnp.name
}

output "db_user" {
  value = scaleway_iam_application.backend.id
}

output "db_password" {
  value     = scaleway_iam_api_key.backend.secret_key
  sensitive = true
}

output "database_url" {
  value     = local.database_url
  sensitive = true
}