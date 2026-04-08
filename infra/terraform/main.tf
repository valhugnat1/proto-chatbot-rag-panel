###############################################################################
# main.tf
#
# Point d'entrée Terraform pour le déploiement BNP Chatbot POC sur Scaleway.
#
# Ordre de lecture conseillé pour comprendre l'infra :
#   1. main.tf       → provider, namespace (= container registry), IAM
#   2. database.tf   → Serverless SQL Database + DSN exporté
#   3. containers.tf → containers serverless backend + frontend
#   4. variables.tf  → toutes les variables d'entrée
#   5. outputs.tf    → URLs publiques + commandes utiles
#
# Avant d'appliquer, exporter ces variables d'environnement :
#   export SCW_ACCESS_KEY=...
#   export SCW_SECRET_KEY=...
#   export SCW_DEFAULT_PROJECT_ID=...
#   export SCW_DEFAULT_REGION=fr-par
#
# Puis :
#   terraform init
#   terraform apply -var "mistral_api_key=..."
###############################################################################

terraform {
  required_version = ">= 1.5"

  required_providers {
    scaleway = {
      source  = "scaleway/scaleway"
      version = ">= 2.40"
    }
    random = {
      source  = "hashicorp/random"
      version = ">= 3.5"
    }
  }
}

provider "scaleway" {
  # Toutes les credentials sont lues depuis l'environnement :
  #   SCW_ACCESS_KEY, SCW_SECRET_KEY, SCW_DEFAULT_PROJECT_ID, SCW_DEFAULT_REGION
  # On force quand même la région ici pour éviter toute surprise.
  region = "fr-par"
}

###############################################################################
# Namespace de containers serverless
#
# Un namespace Scaleway est à la fois :
#   - un groupe logique pour les containers serverless
#   - un Container Registry (rg.fr-par.scw.cloud/<namespace>)
#
# C'est dans ce registry que `build_and_push.sh` poussera les images.
###############################################################################

resource "scaleway_container_namespace" "main" {
  name        = "${var.project_name}-${var.environment}"
  description = "BNP Chatbot POC — namespace + registry"
}

###############################################################################
# IAM application + clé API pour le backend
#
# Le Serverless SQL Database utilise IAM pour l'authentification :
#   - le username est l'ID de l'IAM application (ou user)
#   - le password est la secret key d'une API key liée à cette application
#
# On crée une application dédiée avec uniquement les droits "DatabasesReadWrite"
# sur le projet, plus restrictive que de réutiliser la clé personnelle.
###############################################################################

resource "scaleway_iam_application" "backend" {
  name        = "${var.project_name}-${var.environment}-backend"
  description = "Application IAM utilisée par le backend pour se connecter à la Serverless SQL DB"
}

resource "scaleway_iam_policy" "backend_db" {
  name           = "${var.project_name}-${var.environment}-backend-db"
  description    = "Accès lecture/écriture à la Serverless SQL DB du projet"
  application_id = scaleway_iam_application.backend.id

  rule {
    project_ids          = [var.project_id]
    permission_set_names = ["ServerlessSQLDatabaseReadWrite"]
  }
}

resource "scaleway_iam_api_key" "backend" {
  application_id = scaleway_iam_application.backend.id
  description    = "Clé API utilisée par le backend pour le DSN PostgreSQL"
}
