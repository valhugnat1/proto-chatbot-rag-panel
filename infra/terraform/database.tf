###############################################################################
# database.tf
#
# Serverless SQL Database (pay-per-use, scale-to-zero, pgvector supporté).
#
# Modèle de coûts :
#   - ~0,10 €/mois pour 1 GB au repos (notre cas)
#   - facturation à la requête CPU au-dessus
#
# Limites à connaître :
#   - PostgreSQL 14 uniquement
#   - pas de SUPERUSER → pgvector s'active via CREATE EXTENSION (autorisé)
#   - pas de TEMPORARY TABLES → ETL classiques pas supportés (pas un problème ici)
#   - pas attachable à un Private Network (pour l'instant)
#
# L'extension `vector` doit être créée APRÈS le terraform apply, via le script
# `infra/scripts/bootstrap_pgvector.sh`. Voir le README pour le détail.
###############################################################################

resource "scaleway_sdb_sql_database" "bnp" {
  name       = "${var.project_name}-${var.environment}"
  project_id = var.project_id
  min_cpu    = 0 # scale to zero
  max_cpu    = 4 # cap raisonnable pour un POC
}

###############################################################################
# Construction du DSN pour le backend
#
# Format attendu par langchain-postgres / psycopg3 :
#   postgresql+psycopg://<user>:<password>@<host>:<port>/<database>?sslmode=require
#
# Avec :
#   - user     = ID de l'IAM application (scaleway_iam_application.backend.id)
#   - password = secret key de l'API key (scaleway_iam_api_key.backend.secret_key)
#   - host     = hostname extrait de l'attribut `endpoint` du sdb
#   - database = name du sdb
#
# L'attribut `endpoint` est de la forme :
#   postgres://<dbid>.pg.sdb.fr-par.scw.cloud:5432/<dbname>
# On extrait le hostname avec une regex.
###############################################################################

locals {
  # Exemple d'endpoint : "postgres://abc-123.pg.sdb.fr-par.scw.cloud:5432/bnp-prod"
  # On extrait juste "abc-123.pg.sdb.fr-par.scw.cloud".
  # Note : avec un seul groupe de capture, `regex()` renvoie directement la
  # string capturée (pas une liste). Avec plusieurs groupes, ce serait une liste.
  db_host = regex("postgres://([^:/]+)", scaleway_sdb_sql_database.bnp.endpoint)[0]

  # DSN final, prêt à être injecté comme env var DATABASE_URL.
  database_url = format(
    "postgresql+psycopg://%s:%s@%s:5432/%s?sslmode=require",
    scaleway_iam_application.backend.id,
    scaleway_iam_api_key.backend.secret_key,
    local.db_host,
    scaleway_sdb_sql_database.bnp.name,
  )
}
