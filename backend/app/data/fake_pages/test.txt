# BNP-like Banking Chatbot — POC

A demo-grade multi-agent banking assistant inspired by the BNP Paribas / Mistral AI proposal. FastAPI backend + Vue 3 frontend, runnable end-to-end with `docker compose up`.

**Stack:** FastAPI · LangGraph ReAct agent · Mistral Large · Postgres + pgvector · Vue 3 + Vite

> Out of scope: auth, PSD2/SCA, NeMo Guardrails, production hardening.

---

## Architecture

```text
┌──────────────┐  HTTPS/SSE   ┌──────────────────────────┐
│  Vue.js UI   │ ───────────▶ │  FastAPI Backend         │
│  (nginx)     │              │  ┌────────────────────┐  │
└──────────────┘              │  │ LangGraph ReAct    │  │
                              │  │  ┌──────────────┐  │  │
                              │  │  │ Mistral Large│◀─┼──┼─── api.mistral.ai
                              │  │  └──────────────┘  │  │
                              │  │  ┌──────────────┐  │  │
                              │  │  │ search_kb    │──┼──┼──▶ Postgres + pgvector
                              │  │  │ check_account│──┼──┼──▶ fake_clients.json
                              │  │  └──────────────┘  │  │
                              │  └────────────────────┘  │
                              └──────────────────────────┘
```

---

## Quick start

```bash
git clone <repo> bnp-chatbot-poc && cd bnp-chatbot-poc

# 1. Configure
cp .env.example .env          # then set MISTRAL_API_KEY

# 2. Start everything
docker compose up -d

# 3. (Optional) Index a knowledge base
docker compose exec backend python -m app.rag.ingest \
  --url https://en.wikipedia.org/wiki/BNP_Paribas

# 4. Open the UI
open http://localhost:5173
```

Without ingestion, the agent still works — `search_knowledge_base` just returns an empty-KB message. The `check_account` tool works regardless.

---

## How the agent works

A standard LangGraph ReAct loop built with `create_react_agent`:

1. User message hits `/v1/chat/completions` with full history (stateless server).
2. Graph calls Mistral Large with system prompt + history + tool schemas.
3. Model either answers or emits `tool_calls`.
4. `ToolNode` runs the tools; results are appended as `ToolMessage`s.
5. Loop until a final answer (capped at `recursion_limit=8`).
6. Tokens stream back via `astream_events(version="v2")`.

### Tools

| Tool | What it does | Backed by |
|---|---|---|
| `search_knowledge_base` | Dense retrieval (k=5, cosine threshold 0.5) | `PGVector` + `MistralAIEmbeddings` |
| `check_account` | Case-insensitive name lookup, returns balances | `app/data/fake_clients.json` |

Demo clients: **Jean Dupont**, **Marie Martin**, **Hugo Philipp**.

> ⚠️ `check_account` is intentionally naive — no auth. In a real deployment this would be gated by OIDC + RBAC.

---

## RAG ingestion

```bash
# Defaults: max 20 pages, depth 2
docker compose exec backend python -m app.rag.ingest \
  --url https://en.wikipedia.org/wiki/BNP_Paribas

# Custom limits
docker compose exec backend python -m app.rag.ingest \
  --url https://en.wikipedia.org/wiki/Hello_bank! --max-pages 10 --max-depth 1
```

### Managing the vector store

```bash
docker compose exec db psql -U bnp -d bnp
```

```sql
-- List ingested sources
SELECT DISTINCT cmetadata->>'source' FROM langchain_pg_embedding;

-- Delete one source
DELETE FROM langchain_pg_embedding
WHERE cmetadata->>'source' = 'https://en.wikipedia.org/wiki/BNP_Paribas';

-- Wipe everything
TRUNCATE langchain_pg_embedding;
```

---

## Talking to the backend directly

OpenAI-compatible `POST /v1/chat/completions`.

```bash
# Non-streaming
curl -X POST http://localhost:8000/v1/chat/completions \
  -H 'Content-Type: application/json' \
  -d '{"messages":[{"role":"user","content":"What is Jean Dupont'\''s balance?"}],"stream":false}'

# Streaming
curl -N -X POST http://localhost:8000/v1/chat/completions \
  -H 'Content-Type: application/json' \
  -d '{"messages":[{"role":"user","content":"Tell me about the Visa Premier card."}],"stream":true}'
```

Health: `curl http://localhost:8000/health` · Docs: http://localhost:8000/docs

---

## Frontend

ChatGPT-style Vue 3 SPA. Multi-conversation sidebar (localStorage), SSE token streaming, stop button via `AbortController`, markdown rendering (`marked` + `DOMPurify`), auto-titling, dark theme with green accent, responsive.

### Dev mode (without Docker)

```bash
cd frontend
npm install
echo "VITE_API_URL=http://localhost:8000" > .env
npm run dev
```

---

## Environment variables

| Variable | Required | Default | Description |
|---|---|---|---|
| `MISTRAL_API_KEY` | ✅ | — | Mistral API key |
| `MISTRAL_MODEL` | | `mistral-large-latest` | Chat model |
| `MISTRAL_EMBED_MODEL` | | `mistral-embed` | Embedding model |
| `DATABASE_URL` | | `postgresql+psycopg://bnp:bnp@db:5432/bnp` | psycopg3 DSN |
| `FRONTEND_URL` | | `http://localhost:5173` | CORS allow-origin |
| `VITE_API_URL` | | `http://localhost:8000` | Backend URL baked into frontend |
| `LOG_LEVEL` | | `INFO` | Python logging level |

---

## Tests

```bash
cd backend
pip install -e ".[dev]"
pytest -v
```

Smoke tests don't need a live Mistral key or running Postgres.

---

## Troubleshooting

- **`connection failed`** — wrong host in `DATABASE_URL`. Use `db` from inside compose, `localhost` from your host.
- **`extension "vector" is not available`** — you're on plain `postgres:16`. Use `pgvector/pgvector:pg16`.
- **`401 Unauthorized` from Mistral** — check `MISTRAL_API_KEY`.
- **Frontend "Failed to fetch"** — backend down or CORS. Check `curl http://localhost:8000/health`.
- **Reset local DB**: `docker compose down -v && docker compose up -d db`
- **Reset frontend conversations**: `localStorage.clear()` in browser console.

---

## Production deployment (Scaleway + Terraform)

The `infra/` folder contains Terraform to deploy on Scaleway Serverless Containers + Serverless SQL Database (pgvector enabled).

### Prerequisites

Terraform ≥ 1.5 · Docker with `buildx` · `psql` client · Scaleway account + API key · Mistral API key

### Bootstrap (first deployment)

The frontend bakes the backend URL at build time, so the first deploy is a 2-pass process:

```bash
# 1. Credentials
export SCW_ACCESS_KEY=... SCW_SECRET_KEY=... SCW_DEFAULT_PROJECT_ID=...
export SCW_DEFAULT_REGION=fr-par
export MISTRAL_API_KEY=...

cd infra/terraform
cp terraform.tfvars.example terraform.tfvars   # fill in
terraform init

# 2. Create registry, DB, IAM (no containers yet)
terraform apply \
  -target=scaleway_container_namespace.main \
  -target=scaleway_sdb_sql_database.bnp \
  -target=scaleway_iam_application.backend \
  -target=scaleway_iam_policy.backend_db \
  -target=scaleway_iam_api_key.backend

# 3. Activate pgvector
cd ../scripts && ./bootstrap_pgvector.sh

# 4. Build & push images (placeholder frontend URL on first round)
export REGISTRY=$(cd ../terraform && terraform output -raw registry_endpoint)
export BACKEND_URL="https://placeholder.example.com"
./build_and_push.sh

# 5. Deploy both containers — now we get the real backend URL
cd ../terraform
terraform apply -var "image_tag=$(cat /tmp/bnp-image-tag)"

# 6. Rebuild frontend with the real backend URL, redeploy
export BACKEND_URL=$(terraform output -raw backend_url)
cd ../scripts && ./build_and_push.sh
cd ../terraform
terraform apply -var "image_tag=$(cat /tmp/bnp-image-tag)"
```

### Index the prod KB

```bash
export DATABASE_URL=$(cd infra/terraform && terraform output -raw database_url)
export MISTRAL_API_KEY=...
cd backend
python -m app.rag.ingest --url https://en.wikipedia.org/wiki/BNP_Paribas --max-pages 50
```

### Subsequent deploys

```bash
cd infra/scripts
export BACKEND_URL=$(cd ../terraform && terraform output -raw backend_url)
./build_and_push.sh
cd ../terraform
terraform apply -var "image_tag=$(cat /tmp/bnp-image-tag)"
```

### Teardown

```bash
terraform destroy
```

### Caveats

- **Region**: Serverless SQL Database is only available in `fr-par`.
- **PostgreSQL 14**: no `SUPERUSER`, no `TEMPORARY TABLES`. `pgvector` works fine.
- **No private networking**: backend talks to the DB over public TLS (IAM-auth'd). Acceptable for a POC.
- **State file**: `terraform.tfstate` contains secrets in clear. `.gitignore`d. For real deployments, use a remote backend (S3 on Scaleway Object Storage).

---

## License & disclaimer

Personal proof of concept, not affiliated with BNP Paribas.