###############################################################################
# variables.tf — toutes les variables d'entrée Terraform.
#
# Les variables sans `default` sont obligatoires.
# Toutes les sensitives sont marquées comme telles pour éviter les fuites
# dans les logs Terraform.
###############################################################################

# --- Identification du projet -----------------------------------------------

variable "project_id" {
  type        = string
  description = "ID du projet Scaleway dans lequel déployer (doit matcher SCW_DEFAULT_PROJECT_ID)"
}

variable "project_name" {
  type        = string
  default     = "bnp-chatbot"
  description = "Préfixe utilisé pour nommer toutes les ressources"
}

variable "environment" {
  type        = string
  default     = "prod"
  description = "Suffixe d'environnement (prod, staging, dev)"
}

# --- Mistral ----------------------------------------------------------------

variable "mistral_api_key" {
  type        = string
  sensitive   = true
  description = "Clé API Mistral, injectée comme secret env var dans le backend"
}

variable "mistral_model" {
  type        = string
  default     = "mistral-large-latest"
  description = "Modèle de chat utilisé par l'agent"
}

variable "mistral_embed_model" {
  type        = string
  default     = "mistral-embed"
  description = "Modèle d'embedding utilisé par le RAG"
}

# --- Images Docker ----------------------------------------------------------

variable "image_tag" {
  type        = string
  default     = "latest"
  description = <<-EOT
    Tag d'image à déployer. Utiliser un timestamp (e.g. 20260407-1430) pour
    forcer le redéploiement après un push. Le script build_and_push.sh
    génère ce tag automatiquement.
  EOT
}
