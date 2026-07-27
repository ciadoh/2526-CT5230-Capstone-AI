# TechDebt AI — Capstone Demo

AI-driven technical debt management dashboard. Integrates SonarQube, GitHub, AWS Bedrock, Ollama, MLflow, and Langfuse into a single Vue.js interface — all running in Docker.

## Architecture

```
Vue.js (Nginx :80)
    └── FastAPI backend (:8000)
            ├── SonarQube (:9000)   — static analysis
            ├── GitHub API          — commit/repo/PR data
            ├── AWS Bedrock         — LLM analysis (Nova Micro/Lite/Pro, Mistral)
            ├── Ollama (:11434)     — local LLM (llama3.2:3b)
            ├── MLflow (:5001)      — experiment tracking
            └── Langfuse (:3001)    — LLM observability

PostgreSQL (internal) — shared datastore; four databases (sonarqube, mlflow,
                        langfuse, appdb) created on first boot by scripts/init-db.sh
```

## Quick Start

### 1. Configure environment

```bash
cp .env.example .env
```

Edit `.env` — the minimum required fields:

```env
AWS_ACCESS_KEY_ID=your_key
AWS_SECRET_ACCESS_KEY=your_secret
AWS_DEFAULT_REGION=eu-west-1
GITHUB_TOKEN=your_github_pat   # needs repo:read + write scope for PR creation
```

`.env.example` already ships with working example Langfuse keys
(`LANGFUSE_PUBLIC_KEY` / `LANGFUSE_SECRET_KEY`). Leave them as-is or change them —
they must be set **before** the first `docker compose up` so Langfuse can
auto-provision its project against them (see Step 4). `SONARQUBE_TOKEN` stays
blank for now; you'll generate it in Step 3.

### 2. Start all services

```bash
docker compose up -d
```

Services take ~2 minutes to initialise on first run (SonarQube is the slowest).

### 3. Set up SonarQube token

1. Open http://localhost:9000
2. Log in: `admin` / `admin` (you will be prompted to change the password)
3. Go to **My Account → Security → Generate Tokens**
4. Copy the token into `.env` (user tokens are prefixed `squ_`):
   ```env
   SONARQUBE_TOKEN=squ_xxxxx
   ```
5. Restart the backend: `docker compose restart backend`

### 4. Langfuse (auto-configured)

No manual setup needed. On first boot Langfuse auto-provisions an organisation,
project, and admin user from the `LANGFUSE_INIT_*` values in `docker-compose.yml`,
using the `LANGFUSE_PUBLIC_KEY` / `LANGFUSE_SECRET_KEY` you set in Step 1 — so the
backend can read traces immediately.

To browse traces in the Langfuse UI (http://localhost:3001), log in with:

- **Email:** `admin@techdebt.local`
- **Password:** `changeme_local_pw123` (override via `LANGFUSE_INIT_USER_PASSWORD` in `.env`)

> If you started the stack **before** setting the Langfuse keys, the project was
> created without them. Set the keys in `.env`, then recreate Langfuse so it
> re-provisions: `docker compose up -d --force-recreate langfuse`.

### 5. Run the SonarQube scan

Easiest: click **Run Scan** in the dashboard topbar. The backend builds the scanner
image if needed and runs it against the currently selected repository (via the
mounted Docker socket), polling for completion.

Or from the CLI:

```bash
docker compose --profile scan run --rm scanner
```

Either way this clones the target repo, creates the SonarQube project, and runs the scanner (~5 minutes). Once complete, dashboard metrics and the File Risk Heatmap will populate automatically.

Java/Maven projects (e.g. WebGoat) are detected automatically and compiled before scanning.

### 6. Open the dashboard

http://localhost:80

---

## Features

| Feature | Description |
|---|---|
| **Dashboard** | Repo overview, SonarQube risk score, language breakdown |
| **Issues** | SonarQube issues with per-issue AI analysis and one-click fix PR |
| **File Risk Heatmap** | Per-file rule-based + ML risk scores (LR + RF), churn, severity, pagination |
| **ML Training** | Train logistic regression and random forest on file metrics; ROC curve + score distribution charts |
| **AI Analysis** | Debt analysis via Bedrock or Ollama; side-by-side model comparison |
| **MLflow** | Experiment runs tracked automatically on every risk score and ML train |
| **Langfuse** | Full LLM observability — traces for analyse, issue review, compare, and PR generation |

---

## AWS Bedrock Requirements

The following models must be enabled in your AWS account under **Bedrock → Model access** (EU region):

| Alias | Model ID |
|---|---|
| `nova-micro` | `eu.amazon.nova-micro-v1:0` |
| `nova-lite` | `eu.amazon.nova-lite-v1:0` |
| `nova-pro` | `eu.amazon.nova-pro-v1:0` |
| `mistral` | `mistral.mixtral-8x7b-instruct-v0:1` |

Enable them at: AWS Console → Bedrock → Model access → Request access.

> If using a different region, update the model IDs in `backend/app/services/bedrock_client.py`.

---

## Local LLM (Ollama)

Ollama runs as a service in Docker and pulls `llama3.2:3b` on first startup. Select **"ollama"** from the model dropdown in the AI Analysis or Create PR panels. No AWS credentials required.

> **Behind an SSL-inspecting proxy?** The model pull uses HTTPS, so Ollama must trust
> your proxy's CA. A combined CA bundle (public roots + corporate chain) is provided at
> `certs/ca-bundle.pem` and mounted into the container (`SSL_CERT_FILE`). If pulls fail
> with `x509: certificate signed by unknown authority`, regenerate the bundle for your
> network and replace `certs/ca-bundle.pem`, then `docker compose up -d --force-recreate ollama`.

---

## Supported Repositories

The dashboard supports switching between repositories via the dropdown. The following repos are pre-configured:

| Repo | PR creation |
|---|---|
| `expressjs/express` | Read-only |
| `ciadoh/NodeGoat` | ✅ |
| `ciadoh/juice-shop` | ✅ |
| `ciadoh/WebGoat` | ✅ |

PR creation requires the `GITHUB_TOKEN` to have write access to the repo.

---

## Service URLs

| Service | URL | Purpose |
|---|---|---|
| Dashboard | http://localhost:80 | Main UI |
| FastAPI docs | http://localhost:8000/docs | API explorer |
| SonarQube | http://localhost:9000 | Code analysis UI |
| MLflow | http://localhost:5001 | Experiment tracking UI |
| Langfuse | http://localhost:3001 | LLM observability UI |

## Useful commands

```bash
# Tail backend logs
docker compose logs -f backend

# Re-run sonar scan
docker compose --profile scan run --rm scanner

# Rebuild after frontend/nginx changes
docker compose build frontend && docker compose up -d frontend

# Rebuild after backend dependency changes
docker compose build backend && docker compose up -d backend

# Reset all data (destructive)
docker compose down -v
```

## Changing the target repository

Use the repository dropdown in the dashboard UI to switch between configured repos. To add a new repo, add it to `AVAILABLE_REPOS` in `backend/app/state.py` and rebuild the backend.
