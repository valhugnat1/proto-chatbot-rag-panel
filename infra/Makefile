# BNP Chatbot — infra commands
#
# Usage:
#   make bootstrap   # first-time setup (registry + DB + pgvector, then full deploy)
#   make deploy      # build, push, and deploy a new version
#   make destroy     # tear everything down
#   make urls        # print frontend/backend URLs
#   make db-shell    # open psql on the prod DB

SHELL := /bin/bash
TF    := cd terraform && terraform
TAG   := $(shell date +%Y%m%d-%H%M%S)

.PHONY: bootstrap deploy destroy urls db-shell _build _check-env

_check-env:
	@: $${SCW_ACCESS_KEY?missing} $${SCW_SECRET_KEY?missing} $${SCW_DEFAULT_PROJECT_ID?missing} $${MISTRAL_API_KEY?missing}

bootstrap: _check-env
	$(TF) init
	$(TF) apply -auto-approve \
	  -target=scaleway_container_namespace.main \
	  -target=scaleway_sdb_sql_database.bnp \
	  -target=scaleway_iam_policy.backend_db \
	  -target=scaleway_iam_api_key.backend \
	  -target=scaleway_iam_policy.backend_db
	./scripts/pgvector.sh
	BACKEND_URL=https://placeholder.example.com $(MAKE) _build TAG=$(TAG)
	$(TF) apply -auto-approve -var "image_tag=$(TAG)"
	$(MAKE) deploy

deploy: _check-env
	$(eval BACKEND_URL := $(shell $(TF) output -raw backend_url))
	BACKEND_URL=$(BACKEND_URL) $(MAKE) _build TAG=$(TAG)
	$(TF) apply -auto-approve -var "image_tag=$(TAG)"
	@echo "Deployed. Frontend: $$($(TF) output -raw frontend_url)"

_build:
	$(eval REGISTRY := $(shell $(TF) output -raw registry_endpoint))
	./scripts/build.sh $(REGISTRY) $(TAG) $(BACKEND_URL)

destroy:
	$(TF) destroy

urls:
	@echo "Frontend: $$($(TF) output -raw frontend_url)"
	@echo "Backend:  $$($(TF) output -raw backend_url)"
	@echo "Database URL: $$($(TF) output -raw database_url)"


db-shell:
	@PGPASSWORD=$$($(TF) output -raw db_password) psql \
	  "host=$$($(TF) output -raw db_host) port=5432 \
	   dbname=$$($(TF) output -raw db_name) \
	   user=$$($(TF) output -raw db_user) sslmode=require"