# JapanLife Plan 3 — 部署与打磨 Implementation Plan

> **For agentic workers:** Plan 3 is infrastructure + documentation (Dockerfile, docker-compose, CI, eval report, README). Unlike Plans 1–2 it is not unit-TDD; each task is verified by **building/booting** the artifact (`docker compose config/build/up`, `/health`, `make eval`) and by keeping the existing test suite green. Steps use checkbox (`- [ ]`) syntax.

**Goal:** Make the project a one-command, portfolio-grade deliverable: containerize the FastAPI app, wire it into docker-compose with ES + Qdrant, add CI that runs the unit tests, commit an honest retrieval eval report, and rewrite the README as a strong landing page.

**Architecture:** A slim Python image runs `uvicorn app.main:app`; in the compose network it reaches `elasticsearch:9200` / `qdrant:6333` (service names) and reads `DEEPSEEK_API_KEY` from `.env`. Hugging Face model cache and the SQLite checkpoint live on named volumes. CI installs deps via Poetry and runs `pytest -m "not integration"`.

**Tech Stack:** Docker / docker-compose, GitHub Actions, Poetry. Builds on Plan 1 (retrieval) + Plan 2 (agents + API).

Reference spec: `docs/superpowers/specs/2026-06-09-japanlife-langgraph-refactor-design.md` (§11–12, §15).

---

## File Structure (Plan 3)

| 文件 | 职责 |
|---|---|
| `Dockerfile` | FastAPI app image (poetry → uvicorn) |
| `.dockerignore` | keep the build context small |
| `docker-compose.yml` | add `api` service (network URLs, env_file, volumes, depends_on healthy) |
| `Makefile` | `build` / `up` / `down` / `serve` / `logs` / `ingest-docker` targets |
| `.github/workflows/ci.yml` | CI: poetry install + unit tests |
| `docs/eval-report.md` | committed retrieval eval (hybrid vs baselines) |
| `README.md` | comprehensive portfolio README |

---

## Task 1: API Dockerfile + .dockerignore

- [ ] **Create `Dockerfile`**
```dockerfile
FROM python:3.13-slim

ENV PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1 \
    POETRY_VERSION=2.3.4 \
    POETRY_VIRTUALENVS_CREATE=false

WORKDIR /app

RUN pip install --no-cache-dir "poetry==${POETRY_VERSION}"

COPY pyproject.toml poetry.lock ./
RUN poetry install --only main --no-interaction --no-ansi

COPY core ./core
COPY rag ./rag
COPY agents ./agents
COPY tools ./tools
COPY app ./app
COPY knowledge ./knowledge

EXPOSE 8000
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
```

- [ ] **Create `.dockerignore`**
```
.git
.venv
__pycache__
*.pyc
.pytest_cache
.mypy_cache
chroma_db
docs
tests
eval
.worktrees
*.db
.env
.idea
.DS_Store
```

- [ ] **Verify build:** `docker compose build api` succeeds (heavy: installs torch + sentence-transformers).

## Task 2: docker-compose api service

- [ ] **Add an `api` service** to `docker-compose.yml` and two named volumes. The `environment` block overrides the localhost URLs from `.env` with compose service names; `env_file` supplies `DEEPSEEK_API_KEY`.
```yaml
  api:
    build: .
    container_name: japanlife-api
    env_file: .env
    environment:
      - ES_URL=http://elasticsearch:9200
      - QDRANT_URL=http://qdrant:6333
      - CHECKPOINT_DB=/app/data/japanlife.db
    ports:
      - "8000:8000"
    depends_on:
      elasticsearch:
        condition: service_healthy
      qdrant:
        condition: service_started
    volumes:
      - hf_cache:/root/.cache/huggingface
      - api_data:/app/data
```
```yaml
volumes:
  qdrant_storage:
  hf_cache:
  api_data:
```
- [ ] **Validate:** `docker compose config` parses cleanly.

## Task 3: Boot full stack + verify /health

- [ ] `docker compose up -d` (ES + Qdrant + api). Wait for ES healthy.
- [ ] `curl -s localhost:8000/health` → `{"status":"ok","elasticsearch":true,"qdrant":true}` (api reaches ES/Qdrant via the compose network).
- [ ] Knowledge is already ingested in the running ES/Qdrant (Plan 1). To (re)ingest inside the stack: `docker compose run --rm api python -m rag.ingest`.

## Task 4: CI workflow

- [ ] **Create `.github/workflows/ci.yml`**
```yaml
name: CI

on:
  push:
    branches: [main]
  pull_request:

jobs:
  test:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-python@v5
        with:
          python-version: "3.13"
      - name: Install Poetry
        run: pipx install poetry
      - name: Install dependencies
        run: poetry install --with dev --no-interaction
      - name: Run unit tests
        run: poetry run pytest -q -m "not integration"
```
- [ ] **Validate:** YAML parses; the test command matches the locally-green `pytest -m "not integration"`.

## Task 5: Eval report

- [ ] Run `make eval` (services up + ingested) and capture the metrics.
- [ ] **Create `docs/eval-report.md`** with the methodology, the hybrid-vs-baseline table, and an honest interpretation (small corpus → dense saturates; hybrid's edge is at scale / rare-term queries).

## Task 6: Makefile targets + README polish

- [ ] **Add Makefile targets:** `build`, `up` (already), `down` (already), `logs`, `ingest-docker`.
```makefile
build:
	docker compose build

logs:
	docker compose logs -f api

ingest-docker:
	docker compose run --rm api python -m rag.ingest
```
- [ ] **Rewrite `README.md`** as a portfolio landing page: one-line pitch, feature highlights, both architecture diagrams (retrieval + agents), one-command quickstart (`make up` → `make ingest` → `make serve`/compose api), API examples, the eval report link/table, tech stack, project structure, test commands, and a roadmap. Keep the honest eval note.

## Task 7: Verify + PR

- [ ] `poetry run pytest -q -m "not integration"` stays green.
- [ ] `docker compose config` valid; api image builds; `/health` ok.
- [ ] Commit each task; push `feat/deploy-polish`; open PR #3 (base `feat/multi-agent-api`).

---

## Notes
- The api image is large (torch + sentence-transformers) and downloads BGE models on first retrieval call; the `hf_cache` volume avoids re-downloading. `/health` boots without any model download, so it is the cheap end-to-end check.
- `.env` is git-ignored and only read at runtime (never baked into the image; `.dockerignore` excludes it).
- Live `/chat` requires `DEEPSEEK_API_KEY` in `.env` (already verified end-to-end on the host in Plan 2).
