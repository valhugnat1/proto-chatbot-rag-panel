###############################################################################
# outputs.tf
#
# Outputs visibles après `terraform apply`. Les outputs sensibles (DSN, secret
# key) sont marqués `sensitive = true` pour ne pas apparaître dans les logs.
# Pour les afficher en clair :
#   terraform output -raw database_url
#   terraform output -raw db_user
#   terraform output -raw db_password
###############################################################################

# --- URLs publiques ---------------------------------------------------------

output "frontend_url" {
  value       = "https://${scaleway_container.frontend.domain_name}"
  description = "URL publique du frontend Vue (ouverte dans le navigateur)"
}

output "backend_url" {
  value       = "https://${scaleway_container.backend.domain_name}"
  description = "URL publique de l'API backend (utilisée par VITE_API_URL au build)"
}

# --- Registry pour build_and_push.sh ----------------------------------------

output "registry_endpoint" {
  value       = scaleway_container_namespace.main.registry_endpoint
  description = "Endpoint du Container Registry (à exporter pour le script de build)"
}

# --- Database (sensitive) ---------------------------------------------------

output "database_url" {
  value       = local.database_url
  sensitive   = true
  description = "DSN PostgreSQL complet (postgresql+psycopg://...) — utilisé par le backend"
}

output "db_host" {
  value       = local.db_host
  description = "Hostname de la Serverless SQL Database"
}

output "db_name" {
  value       = scaleway_sdb_sql_database.bnp.name
  description = "Nom de la Serverless SQL Database"
}

output "db_user" {
  value       = scaleway_iam_application.backend.id
  description = "Username PostgreSQL (= ID de l'IAM application backend)"
}

output "db_password" {
  value       = scaleway_iam_api_key.backend.secret_key
  sensitive   = true
  description = "Password PostgreSQL (= secret key de l'IAM API key)"
}

# --- Commandes prêtes à copier-coller ---------------------------------------

output "next_steps" {
  description = "Commandes à exécuter après le premier `terraform apply`"
  value       = <<-EOT

    ════════════════════════════════════════════════════════════════════
    🎉  Infrastructure déployée avec succès !
    ════════════════════════════════════════════════════════════════════

    URLs publiques :
      Frontend : https://${scaleway_container.frontend.domain_name}
      Backend  : https://${scaleway_container.backend.domain_name}
      Health   : https://${scaleway_container.backend.domain_name}/health

    ─── Étapes restantes ───────────────────────────────────────────────

    1️⃣  Activer pgvector dans la base (à faire UNE SEULE FOIS) :

        cd ../scripts
        ./bootstrap_pgvector.sh

    2️⃣  Indexer la base de connaissances depuis votre poste local :

        export DATABASE_URL='$(terraform output -raw database_url)'
        export MISTRAL_API_KEY=...
        cd ../../backend
        python -m app.rag.ingest all --max-pages 50 --max-depth 2

        (alternativement, exécutable dans un container one-shot)

    3️⃣  Ouvrir le frontend :

        open https://${scaleway_container.frontend.domain_name}

    ════════════════════════════════════════════════════════════════════
  EOT
}
