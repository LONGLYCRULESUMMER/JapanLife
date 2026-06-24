# JapanLife — 在日外国人智能助手

A multi-agent AI assistant that helps foreigners living in Japan navigate **tax, visa, and
ward-office** procedures — grounded in a bilingual (EN/JA) knowledge base with **hybrid
retrieval** and orchestrated with **LangGraph**.

**Stack:** Python · LangGraph · LangChain · DeepSeek · ElasticSearch (BM25 + kuromoji) ·
Qdrant (BGE-m3) · FastAPI · Docker

---

## What it does

Ask a question in English or Japanese. A **supervisor** routes it to the right specialist
(**tax / visa / ward_office**), which answers using deterministic domain tools (calculators,
checklists) and **cited** retrieval from an authoritative knowledge base. The ward-office agent
can **hand off** to the visa/tax agents for cross-cutting procedures.

```
You: When is the income tax filing deadline, and what is furusato nozei?
→ routed to: tax
Assistant: Filing runs Feb 16 – Mar 15 (確定申告)… Furusato Nozei lets you donate to
           municipalities and deduct it from your taxes…
Sources: [1] 04-furusato-nozei …  [2] 03-deductions-guide …
```

## Highlights

- **Hybrid RAG** — ElasticSearch BM25 (+ `kuromoji` Japanese tokenizer) **and** Qdrant dense
  vectors (BGE-m3), fused with Reciprocal Rank Fusion and re-ranked by a `bge-reranker-v2-m3`
  cross-encoder. Degrades gracefully if one store is down.
- **Multi-agent orchestration** — LangGraph supervisor + three specialist ReAct agents + an
  explicit specialist→specialist handoff. State persisted per `thread_id`.
- **Tool use** — income-tax estimator, furusato-nozei limit, permanent-residency eligibility,
  moving-in checklist & deadline, plus domain-scoped knowledge search.
- **Bilingual** — answers in the user's language; retrieval handles EN + JA.
- **Production-minded API** — FastAPI `/chat`, SSE `/chat/stream`, `/search`, `/health`,
  async `/admin/ingest` jobs; error handling, recursion limits, graceful failure.
- **Backend engineering** — config-gated embedding + retrieval caches (swappable for Redis)
  and background ingest jobs with a thread-safe registry. See
  [`docs/backend-engineering.md`](docs/backend-engineering.md).
- **Two-axis evaluation** — retrieval eval (Recall@5 / MRR over 95 cases) **and** answer eval
  (citation grounding, disclaimer, language, routing), runnable offline. See
  [`docs/rag-evaluation.md`](docs/rag-evaluation.md).
- **One command to run** — `docker compose up` starts ElasticSearch, Qdrant, and the API.
- **Tested** — 121 unit tests + integration tests; CI on every PR.

## Why this is a backend project (not a prompt demo)

The "AI" is one layer; most of the work is ordinary backend engineering that happens to wrap an
LLM:

- **A real retrieval system, not a vector-store call** — sparse (BM25 + kuromoji) *and* dense
  (BGE-m3) retrieval, fused with RRF and reranked by a cross-encoder, with **graceful
  degradation** when a store is down. Tuned and *measured*, not assumed.
- **Evaluated, not vibe-checked** — separate retrieval and answer evaluations with explicit
  metrics and datasets, runnable in CI without a key.
- **Performance & operability** — embedding/retrieval **caches** behind clean interfaces, and a
  long-running ingest exposed as an **async job** with status/error tracking.
- **Correctness & safety** — deterministic tools for numbers, deterministic graph termination,
  citation extraction, and disclaimers on high-risk answers.
- **Boundaries are explicit** — secrets stay in `.env`; concurrency limits, single-process
  caveats, and production TODOs are written down, not hidden.

It is honestly a **portfolio/learning** system: the knowledge base is demo-grade and the tools
produce estimates, not legal or tax advice.

## Interview walkthrough

A suggested order for explaining the project, each backed by a file you can open:

1. **Architecture** — trace one `/chat` request end to end
   ([`docs/architecture.md`](docs/architecture.md)): API → supervisor routing → ReAct
   specialist → tools / hybrid RAG → citations → state persistence.
2. **RAG** — `rag/retriever.py`: BM25 + dense → RRF (`rag/hybrid.py`) → rerank
   (`rag/rerank.py`), and how it degrades when ES or Qdrant fails.
3. **Agents** — `agents/supervisor.py` (structured-output routing + deterministic backstop) and
   `agents/specialists/` + `tools/` (function-calling, handoff).
4. **Evaluation** — `docs/rag-evaluation.md`: retrieval vs answer eval, the metrics, and how the
   answer eval runs offline with a stub.
5. **Backend engineering** — `docs/backend-engineering.md`: caching, async ingest jobs, error
   handling, degradation, and the observability roadmap.
6. **Production TODO** — Postgres checkpointer, Redis caches, a durable job queue, auth /
   rate-limiting on `/admin/*`, and tracing/metrics.

## Architecture

**Retrieval pipeline**

```
query ─▶ embed (BGE-m3) ─┬─▶ Qdrant         (dense / semantic)      ─┐
                         └─▶ ElasticSearch  (BM25 + kuromoji)        ┴─▶ RRF fuse ─▶ rerank ─▶ cited chunks
```

**Agent graph**

```
                 user (EN/JA)  ──POST /chat──▶  FastAPI
                                                  │
                                          ┌───────▼────────┐
                                          │   Supervisor   │  route by domain (DeepSeek)
                                          └───┬───┬───┬────┘
                                  ┌───────────┘   │   └───────────┐
                                  ▼               ▼               ▼
                                 tax            visa          ward_office ──handoff──▶ visa / tax
                                 agent          agent             agent
                                  └──────── tools(@tool) + hybrid knowledge search ───────┘
                          (conversation state persisted per thread_id via SQLite checkpointer)
```

## Quickstart

### With Docker (recommended)

```bash
cp .env.example .env          # then set DEEPSEEK_API_KEY
make up                       # ElasticSearch (+kuromoji), Qdrant, and the API
make ingest-docker            # index knowledge/ into both stores (first run downloads models)

curl -s localhost:8000/health
curl -s localhost:8000/chat -H 'content-type: application/json' \
  -d '{"message":"When is the tax filing deadline?"}'
```

### Local development

```bash
make install                  # poetry install
make up                       # start ES + Qdrant (+ api)
make ingest                   # index knowledge/ from the host
make serve                    # FastAPI at http://localhost:8000
make test                     # unit tests (no services needed)
make test-all                 # + integration tests (needs services, model downloads, API key)
make eval                     # hybrid vs es-only / qdrant-only retrieval metrics
make answer-eval-stub         # answer-level eval, fully offline (no key/services)
make answer-eval              # answer-level eval with the real agent (needs API key)
```

## API

| Method | Path | Body | Response |
|---|---|---|---|
| POST | `/chat` | `{"message": str, "thread_id"?: str}` | `{reply, citations[], thread_id, route}` |
| POST | `/chat/stream` | same | Server-Sent Events (`update` / `done` / `error`) |
| GET | `/search` | `?q=&domain=&top_k=` | `{query, domain, results[]}` (ranked chunks) |
| GET | `/health` | — | `{status, elasticsearch, qdrant}` |
| POST | `/admin/ingest` | — | `202` + `{id, status, ...}` (async ingest job) |
| GET | `/admin/ingest/jobs` | — | `{jobs[]}` (most recent first) |
| GET | `/admin/ingest/jobs/{id}` | — | one job (`id, status, chunks_indexed, error, ...`) |

## Frontend

The primary product frontend is a Next.js App Router app in `web/`. It talks to the FastAPI
backend through Next.js API proxies by default.

- `/` - product landing page
- `/chat` - user-facing Agent chat and retrieval inspector
- `/admin/login` - admin login
- `/admin/knowledge` - knowledge-base admin console

```bash
make up           # start ElasticSearch, Qdrant, and the FastAPI backend
make web-install  # install Next.js dependencies
make web-dev      # Next.js at http://localhost:3000
```

If the backend is not at `http://localhost:8000`, set `API_URL` for the Next.js server-side proxy.
Set `NEXT_PUBLIC_API_URL` only when the browser should call a different API base directly instead
of the default `/api` proxy. Set `ADMIN_TOKEN` for the UI admin login and cookie gate, and
`ADMIN_API_KEY` for the FastAPI admin API that backs knowledge management.

The old Streamlit demo remains available as an optional legacy surface:

```bash
make demo
```

## Evaluation

JapanLife measures two different things (full design in
[`docs/rag-evaluation.md`](docs/rag-evaluation.md), results in
[`docs/eval-report.md`](docs/eval-report.md)):

- **Retrieval eval** (`make eval`) — Recall@5 / MRR over **95 cases** (≥31 per domain, EN/JA/
  mixed, keyword/semantic/numeric/cross-domain/confusing), comparing `es_only`, `qdrant_only`,
  and `hybrid` (RRF + rerank).
- **Answer eval** (`make answer-eval` / `make answer-eval-stub`) — scores the agent's answers:
  `citation_present`, `citation_supported`, `refusal_or_disclaimer`, `language_match`,
  `route_correct`. Runs against the real agent with `DEEPSEEK_API_KEY`, or fully offline with a
  deterministic stub (`--stub`), so CI never needs a key or services.

Reference retrieval numbers (measured on the earlier small corpus; regenerate on the current
corpus with `make up && make ingest && make eval`):

| Method | Recall@5 | MRR |
|---|---|---|
| es_only (BM25 + kuromoji) | 1.000 | 0.833 |
| qdrant_only (BGE-m3 dense) | 1.000 | 1.000 |
| **hybrid (RRF + rerank)** | **1.000** | **0.929** |

On a small corpus dense retrieval already saturates rank-1, so hybrid does not beat it here;
its advantage shows at scale and on rare-term / exact-match queries (proper nouns, numbers,
Japanese terms). Metrics are reported as-is, not tuned to win.

## Tech stack

| Concern | Choice |
|---|---|
| Orchestration | LangGraph (supervisor + ReAct specialists + handoff) |
| LLM | DeepSeek (`langchain-deepseek`), swappable in one place (`core/llm.py`) |
| Sparse retrieval | ElasticSearch BM25 + `kuromoji` |
| Dense retrieval | Qdrant + BGE-m3 embeddings |
| Fusion / rerank | Reciprocal Rank Fusion + `bge-reranker-v2-m3` |
| Caching | SQLite embedding cache + in-memory retrieval TTL cache (`rag/cache.py`, Redis-swappable) |
| Background work | FastAPI `BackgroundTasks` + thread-safe job registry (`app/jobs.py`) |
| Evaluation | retrieval (Recall@5 / MRR) + answer-level metrics, offline-runnable (`eval/`) |
| State | LangGraph SQLite checkpointer |
| API | FastAPI (+ SSE) |
| Packaging | Poetry, Docker, docker-compose |

## Project structure

```
core/        config (pydantic-settings), DeepSeek LLM factory, language detection
rag/         chunking, embeddings, es_store, qdrant_store, hybrid (RRF), rerank, retriever, ingest, cache
tools/       tax / visa / ward_office calculators + domain-scoped knowledge tool
agents/      state, prompts, supervisor, handoffs, specialists/, graph, output
app/         FastAPI: schemas, routes (/chat, /chat/stream, /search, /health, /admin/ingest), jobs, main (lifespan)
knowledge/   bilingual (EN + native JA) markdown knowledge base — 50 docs across tax / visa / ward_office, front-matter w/ source_url
eval/        retrieval eval (recall@k, MRR) + answer eval (metrics + runner) + datasets
docs/        architecture, rag-evaluation, backend-engineering, eval-report
docker/      custom ElasticSearch image (kuromoji)
streamlit_app.py   decoupled Streamlit demo UI (overview, chat, retrieval inspector)
```

## Testing & CI

```bash
make test            # 121 unit tests, no services or API key required
make test-all        # + integration tests (real ES/Qdrant, model downloads, DEEPSEEK_API_KEY)
make cache-test      # just the cache tests
make answer-eval-stub # answer-eval metrics offline (no key/services)
```

GitHub Actions runs the unit suite on every push/PR (`.github/workflows/ci.yml`). Integration
tests skip automatically when `DEEPSEEK_API_KEY` / services are absent.

## Roadmap

- More domains (banking, employment, housing).
- Production hardening: Postgres checkpointer, Redis-backed caches, a durable job queue, and
  auth / rate-limiting on `/admin/*`.
- Retrieval & answer observability: latency, cache hit rate, hit distribution, and tracing
  (see [`docs/backend-engineering.md`](docs/backend-engineering.md)).
- Promote the answer-eval `LLMJudge` from interface to a wired-in grader for faithfulness.

## Notes

`DEEPSEEK_API_KEY` lives only in the git-ignored `.env` and is read at runtime (never baked into
the image). This is a learning/portfolio project; tool outputs are estimates and not legal or
tax advice.
