# BNP-like Banking Chatbot — POC

A demo-grade multi-agent banking assistant inspired by the BNP Paribas /
Mistral AI proposal. Backend + Vue frontend, runnable end-to-end on a
single machine with `docker compose up`.

**Stack:**
- **Backend** — FastAPI + LangGraph ReAct agent + Mistral Large +
  pgvector RAG over `group.bnpparibas`
- **Frontend** — Vue 3 + Vite, ChatGPT-like UI with multi-conversation
  state, SSE token streaming, markdown rendering
- **DB** — Postgres 16 + pgvector

This POC deliberately leaves out: auth, PSD2/SCA, NeMo Guardrails, Scaleway
Terraform deployment. See [Out of scope](#out-of-scope-deliberately).

---

## Repo layout

```
bnp-chatbot-poc/
├── docker-compose.yml          # db + backend + frontend (local)
├── .env.example
├── infra/
│   ├── init-pgvector.sql       # local: CREATE EXTENSION vector;
│   ├── terraform/              # Scaleway deployment
│   │   ├── main.tf             # provider, namespace, IAM
│   │   ├── database.tf         # Serverless SQL DB + DSN
│   │   ├── containers.tf       # backend + frontend containers
│   │   ├── variables.tf
│   │   ├── outputs.tf
│   │   └── terraform.tfvars.example
│   └── scripts/
│       ├── build_and_push.sh   # buildx amd64 → Scaleway registry
│       └── bootstrap_pgvector.sh
├── backend/
│   ├── Dockerfile
│   ├── pyproject.toml
│   ├── langgraph.json
│   └── app/
│       ├── main.py             # FastAPI app
│       ├── config.py
│       ├── api/                # /health, /v1/chat/completions (SSE)
│       ├── agent/              # LangGraph ReAct agent (canonical layout)
│       │   ├── agent.py
│       │   └── utils/          # state, prompts, tools, nodes
│       ├── rag/                # vector store + scraper + ingest CLI
│       └── data/
│           ├── fake_clients.json
│           └── scraped/        # gitignored cache
└── frontend/
    ├── Dockerfile              # node build → nginx serve
    ├── nginx.conf
    ├── package.json            # vue 3, vite, marked, dompurify
    ├── vite.config.js
    ├── index.html
    └── src/
        ├── main.js
        ├── style.css           # dark theme + BNP green accent
        ├── App.vue             # shell, multi-conv state, streaming
        ├── services/api.js     # SSE client (async generator)
        └── components/
            ├── Sidebar.vue
            ├── WelcomeScreen.vue
            ├── MessageBubble.vue
            └── ChatInput.vue
```

---

## Architecture

```
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

## Quick start (full stack with Docker)

```bash
git clone <repo> bnp-chatbot-poc && cd bnp-chatbot-poc

# 1. Configure
cp .env.example .env
# Edit .env and set MISTRAL_API_KEY

# 2. Start everything
docker compose up -d
docker compose ps   # wait for db to be healthy

# 3. (Optional but recommended) Index the BNP knowledge base
docker compose exec backend python -m app.rag.ingest all --max-pages 50 --max-depth 2

# 4. Open the UI
open http://localhost:5173
```

Without ingestion, the agent still works but `search_knowledge_base` will
return a friendly "the knowledge base hasn't been indexed yet" message.
The `check_account` tool works regardless.

---

## RAG ingestion (with parameters)

The ingestion CLI now accepts full configuration. Three commands, all with
flags:

```bash
# Defaults: 400 pages, depth 3, ~5 min
docker compose exec backend python -m app.rag.ingest all

# Quick demo: ~20 pages, depth 2, faster crawling (~30s total)
docker compose exec backend python -m app.rag.ingest all \
  --max-pages 20 --max-depth 2 --delay 0.3

# Big run: 1000 pages, depth 4
docker compose exec backend python -m app.rag.ingest all \
  --max-pages 1000 --max-depth 4

# Tweak chunking without re-crawling (uses the cached pages.jsonl)
docker compose exec backend python -m app.rag.ingest index \
  --chunk-size 1500 --chunk-overlap 200

# Crawl a different starting URL
docker compose exec backend python -m app.rag.ingest scrape \
  --seed-url https://group.bnpparibas/en/ --max-pages 100
```

### All available flags

| Subcommand | Flag                | Default            | Description                            |
|------------|---------------------|--------------------|----------------------------------------|
| scrape     | `--seed-url`        | `https://group.bnpparibas/` | Starting URL of the BFS crawl |
| scrape     | `--max-pages`       | `400`              | Hard cap on scraped pages              |
| scrape     | `--max-depth`       | `3`                | Maximum BFS depth                      |
| scrape     | `--delay`           | `0.75`             | Politeness delay (seconds) per request |
| index      | `--chunk-size`      | `1000`             | Character chunk size                   |
| index      | `--chunk-overlap`   | `150`              | Character overlap between chunks       |
| index      | `--batch-size`      | `50`               | Documents per embedding upsert batch   |
| all        | *(all of the above)*| —                  | Both subcommands' flags combined       |

`scrape` writes `backend/app/data/scraped/pages.jsonl`. The cache lets you
re-run `index` with new chunking parameters without re-crawling. Stable IDs
(`{url}::{chunk_index}`) make `index` idempotent — re-runs upsert.

### Get help anytime

```bash
docker compose exec backend python -m app.rag.ingest --help
docker compose exec backend python -m app.rag.ingest all --help
```

---

## Frontend

A ChatGPT-style Vue 3 SPA. Features:

- **Multi-conversation** sidebar persisted in `localStorage`
- **SSE streaming** with token-by-token rendering
- **Stop button** mid-stream (via `AbortController`)
- **Markdown rendering** (`marked` + `DOMPurify` sanitization)
- **Auto-titling** from the first user message
- **Welcome screen** with sample prompts (Visa Premier, Jean Dupont solde, etc.)
- **Dark theme**, BNP green (`#00915a`) accents
- **Responsive** (sidebar collapses on mobile)

### How to init the Vue project from scratch

If you'd rather build it yourself (instead of using the files in `frontend/`),
here are the canonical commands:

```bash
# From the repo root, scaffold a Vue 3 + Vite project
npm create vite@latest frontend -- --template vue
cd frontend

# Install dependencies (Vue + Vite are added by the template)
npm install

# Add the runtime deps used by this POC
npm install marked dompurify

# Then drop in:
#   src/App.vue
#   src/main.js
#   src/style.css
#   src/services/api.js
#   src/components/{Sidebar,WelcomeScreen,MessageBubble,ChatInput}.vue
#   .env.example  →  .env  (set VITE_API_URL=http://localhost:8000)
#   Dockerfile, nginx.conf  (only needed for the docker-compose deploy)

# Run dev server
npm run dev   # → http://localhost:5173

# Production build
npm run build
```

The files in `frontend/` are exactly the result of those steps, so the
fastest path is just `docker compose up -d`.

### Running the frontend in dev mode (without Docker)

```bash
cd frontend
npm install
echo "VITE_API_URL=http://localhost:8000" > .env
npm run dev
```

The dev server has hot module reloading and proxies straight to the
backend at `localhost:8000`.

---

## Talking to the backend directly

The backend exposes an OpenAI-compatible `POST /v1/chat/completions`.

**Non-streaming** (great for `curl`):

```bash
curl -X POST http://localhost:8000/v1/chat/completions \
  -H 'Content-Type: application/json' \
  -d '{
    "messages": [
      {"role": "user", "content": "Quel est le solde de Jean Dupont ?"}
    ],
    "stream": false
  }'
```

**Streaming**:

```bash
curl -N -X POST http://localhost:8000/v1/chat/completions \
  -H 'Content-Type: application/json' \
  -d '{
    "messages": [
      {"role": "user", "content": "Parle-moi de la carte Visa Premier."}
    ],
    "stream": true
  }'
```

Health check: `curl http://localhost:8000/health` → `{"status":"ok","db":"ok"}`.

Interactive API docs: <http://localhost:8000/docs>.

---

## How the agent works

A standard LangGraph ReAct loop assembled with `create_react_agent`:

1. The user message arrives at `/v1/chat/completions` with the full
   history (no server-side state — every request is self-contained).
2. The graph calls Mistral Large with the system prompt + history + tool
   schemas bound.
3. The model either answers directly or emits one or more `tool_calls`.
4. The `ToolNode` runs the requested tool(s); their results are appended
   to the message history as `ToolMessage`s.
5. Loop until a final answer (capped at `recursion_limit=8`, ~4 LLM
   iterations).
6. Tokens are streamed back via `astream_events(version="v2")`, filtering
   on `on_chat_model_stream` events.

### The two tools

| Tool                    | What it does                                     | Backed by                       |
|-------------------------|--------------------------------------------------|---------------------------------|
| `search_knowledge_base` | Dense retrieval (k=5, cosine threshold 0.5)      | `langchain_postgres.PGVector` + `MistralAIEmbeddings` |
| `check_account`         | Case-insensitive name lookup, returns balances   | `app/data/fake_clients.json`    |

Fake clients shipped for the demo:

- **Jean Dupont** — Compte courant + Livret A, Visa Premier
- **Marie Martin** — Compte courant à découvert, Visa Classic
- **Hugo Philipp** — Compte courant + Livret A + PEA, Visa Infinite

> ⚠️ The `check_account` tool is intentionally naive: anyone can ask for
> anyone's balance. In the real architecture this would be gated by
> OIDC + RBAC. We assume this for the demo.

---

## Environment variables

| Variable              | Required | Default                                          | Description                          |
|-----------------------|----------|--------------------------------------------------|--------------------------------------|
| `MISTRAL_API_KEY`     | ✅       | —                                                | Mistral API key                      |
| `MISTRAL_MODEL`       |          | `mistral-large-latest`                           | Chat model                           |
| `MISTRAL_EMBED_MODEL` |          | `mistral-embed`                                  | Embedding model                      |
| `DATABASE_URL`        |          | `postgresql+psycopg://bnp:bnp@db:5432/bnp`       | psycopg3 DSN (note the `+psycopg`)   |
| `FRONTEND_URL`        |          | `http://localhost:5173`                          | CORS allow-origin                    |
| `VITE_API_URL`        |          | `http://localhost:8000`                          | Backend URL baked into the frontend  |
| `LOG_LEVEL`           |          | `INFO`                                           | Python logging level                 |

---

## Tests

```bash
cd backend
pip install -e ".[dev]"
pytest -v
```

The smoke tests don't need a live Mistral API key or a running Postgres —
they exercise config loading, the `check_account` tool, and that the
FastAPI app boots with all routes wired.

---

## Running without Docker (faster iteration)

```bash
# 1. Start just postgres in Docker
docker compose up -d db

# 2. Backend in a venv
cd backend
python3.12 -m venv .venv && source .venv/bin/activate
pip install -e .
export MISTRAL_API_KEY=...
export DATABASE_URL=postgresql+psycopg://bnp:bnp@localhost:5432/bnp
uvicorn app.main:app --reload

# 3. Frontend in another terminal
cd frontend
npm install
echo "VITE_API_URL=http://localhost:8000" > .env
npm run dev
```

---

## Troubleshooting

- **`psycopg.OperationalError: connection failed`** — wrong host in
  `DATABASE_URL`. Use `db` from inside docker-compose, `localhost` from
  your host machine.
- **`extension "vector" is not available`** — you're running plain
  `postgres:16`. Use the bundled compose file (`pgvector/pgvector:pg16`).
- **`401 Unauthorized` from Mistral** — `MISTRAL_API_KEY` is unset or
  wrong. Check `docker compose exec backend env | grep MISTRAL`.
- **Frontend says "Erreur : Failed to fetch"** — backend isn't running, or
  CORS is blocking. Check `curl http://localhost:8000/health`.
- **Embedding ingestion is slow / rate-limited** — lower `--batch-size`
  or increase `--delay`.
- **Reset the local DB**: `docker compose down -v && docker compose up -d db`.
- **Reset frontend conversations**: open the browser console and run
  `localStorage.clear()`, or use the trash icon next to each conversation
  in the sidebar.

---

## Production deployment (Scaleway + Terraform)

The `infra/` folder contains a complete Terraform setup to deploy the POC
on Scaleway's serverless products:

- **Serverless SQL Database** — pay-per-use PostgreSQL 14 with pgvector
  (~0.10 €/mois au repos pour 1 GB, facturation au CPU au-delà)
- **Serverless Containers** — backend (`min_scale=1`, pas de cold start) +
  frontend nginx (`min_scale=0`, peut dormir)
- **Container Registry** intégré au namespace
- **IAM dédié** — application least-privilege avec uniquement
  `ServerlessSQLDatabaseReadWrite` sur le projet

Estimated cost at rest: **~5 €/mois** (mostly the backend `min_scale=1`).

### Prerequisites

- Terraform ≥ 1.5 (`brew install terraform`)
- Docker avec `buildx` (inclus avec Docker Desktop)
- `psql` client (`brew install postgresql`)
- Un compte Scaleway avec une API key ayant les droits sur le projet cible
- Un Mac M3 ou équivalent ARM — le script `build_and_push.sh` gère le
  cross-build vers `linux/amd64` automatiquement

### Layout

```
infra/
├── terraform/
│   ├── main.tf                      # provider, namespace, IAM
│   ├── database.tf                  # Serverless SQL DB + DSN
│   ├── containers.tf                # backend + frontend containers
│   ├── variables.tf
│   ├── outputs.tf                   # URLs + next_steps helper
│   └── terraform.tfvars.example
└── scripts/
    ├── build_and_push.sh            # buildx amd64 → Scaleway registry
    └── bootstrap_pgvector.sh        # CREATE EXTENSION vector; (one-shot)
```

### Step 1 — Configure credentials

```bash
# Scaleway credentials (get them from the console)
export SCW_ACCESS_KEY=SCW...
export SCW_SECRET_KEY=...
export SCW_DEFAULT_PROJECT_ID=...
export SCW_DEFAULT_REGION=fr-par

# Mistral
export MISTRAL_API_KEY=...

# Project-local terraform vars
cd infra/terraform
cp terraform.tfvars.example terraform.tfvars
# Edit terraform.tfvars and fill in project_id + mistral_api_key
```

### Step 2 — First apply (bootstrap the registry, DB, and IAM)

Because the frontend image needs the backend URL at build time (Vite env
var baked into the JS bundle), there's a **chicken-and-egg**: we need
Terraform to create the backend container first so we can read its URL,
then rebuild the frontend image. Here's the 6-step procedure:

```bash
# 2a. Init
terraform init

# 2b. First apply — create only the registry, DB, and IAM. This skips
#     the containers for now (no images exist yet).
terraform apply \
  -target=scaleway_container_namespace.main \
  -target=scaleway_sdb_sql_database.bnp \
  -target=scaleway_iam_application.backend \
  -target=scaleway_iam_policy.backend_db \
  -target=scaleway_iam_api_key.backend
```

### Step 3 — Activate pgvector (one-shot)

```bash
cd ../scripts
./bootstrap_pgvector.sh
# → reads terraform outputs, runs `CREATE EXTENSION IF NOT EXISTS vector;`
#   via psql, verifies with `SELECT extname, extversion FROM pg_extension`
```

### Step 4 — First build & push (with a placeholder backend URL)

At this point we don't know the backend URL yet (no container deployed).
We push the images with a placeholder; the frontend built in this round
won't be usable, but the backend will.

```bash
export REGISTRY=$(cd ../terraform && terraform output -raw registry_endpoint)
export BACKEND_URL="https://placeholder.example.com"  # dummy for round 1
./build_and_push.sh
# → pushes backend:$TAG and frontend:$TAG (with broken placeholder)
# → writes the tag to /tmp/bnp-image-tag
```

### Step 5 — Full apply (deploys both containers)

```bash
cd ../terraform
TAG=$(cat /tmp/bnp-image-tag)
terraform apply -var "image_tag=$TAG"
# → creates the backend + frontend containers
# → outputs `backend_url` and `frontend_url` (real this time)
```

### Step 6 — Rebuild frontend with the real backend URL

```bash
export BACKEND_URL=$(terraform output -raw backend_url)
cd ../scripts
./build_and_push.sh
# → rebuilds frontend with VITE_API_URL = real backend URL

cd ../terraform
TAG=$(cat /tmp/bnp-image-tag)
terraform apply -var "image_tag=$TAG"
# → rolls the frontend container to the new image
```

### Step 7 — Index the knowledge base against the prod DB

From your local machine, pointing at the prod DB:

```bash
export DATABASE_URL=$(cd infra/terraform && terraform output -raw database_url)
export MISTRAL_API_KEY=...

cd backend
python -m app.rag.ingest all --max-pages 50 --max-depth 2
```

Alternatively, run a one-shot ingestion container on Scaleway Jobs —
but for a POC, ingesting from your laptop works fine.

### Open the app

```bash
open $(cd infra/terraform && terraform output -raw frontend_url)
```

### Subsequent iterations

Once the initial bootstrap is done, the normal workflow is just 3 commands:

```bash
# Edit code, then:
cd infra/scripts
export BACKEND_URL=$(cd ../terraform && terraform output -raw backend_url)
./build_and_push.sh

cd ../terraform
terraform apply -var "image_tag=$(cat /tmp/bnp-image-tag)"
```

### Tearing it down

```bash
cd infra/terraform
terraform destroy
```

Scaleway will bill you the ~0.10 € for the 1 GB of storage up to the
destroy timestamp. Everything else is pay-per-use and stops immediately.

### Caveats

- **Region**: Serverless SQL Database is **only** available in `fr-par`
  (Paris) as of now.
- **PostgreSQL 14**: the Serverless SQL DB runs Postgres 14. No
  `SUPERUSER`, no `TEMPORARY TABLES`, no `pg_advisory_lock` guarantees.
  `pgvector` works fine via `CREATE EXTENSION`.
- **Private networking**: Serverless SQL DB can't be attached to a
  Scaleway Private Network yet — the backend talks to it over TLS on the
  public endpoint (IAM-auth'd). This is acceptable for a POC.
- **State file**: `terraform.tfstate` contains the Mistral API key and the
  DB password in clear. The `.gitignore` blocks it from being committed.
  For a real deployment, use the S3 backend on Scaleway Object Storage
  (see the Terraform docs).
- **`terraform validate` recommandé avant le premier apply** — je n'ai pas
  pu valider moi-même (accès réseau vers releases.hashicorp.com bloqué
  dans mon environnement). Les fichiers HCL sont bien formés et les noms
  d'attributs viennent directement des docs Scaleway / Terraform Registry
  récents, mais si `terraform validate` remonte un petit attribut
  renommé, ce sera trivial à fixer.

---



---

## License & disclaimer

Personal proof of concept, not affiliated with BNP Paribas. The scraped
content belongs to BNP Paribas; it is used here for demonstration purposes
only and not redistributed.
