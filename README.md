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
- **Production-minded API** — FastAPI `/chat`, SSE `/chat/stream`, `/health`; error handling,
  recursion limits, graceful failure.
- **One command to run** — `docker compose up` starts ElasticSearch, Qdrant, and the API.
- **Tested** — 68 unit tests + integration tests; CI on every PR.

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
```

## API

| Method | Path | Body | Response |
|---|---|---|---|
| POST | `/chat` | `{"message": str, "thread_id"?: str}` | `{reply, citations[], thread_id, route}` |
| POST | `/chat/stream` | same | Server-Sent Events (`update` / `done` / `error`) |
| GET | `/search` | `?q=&domain=&top_k=` | `{query, domain, results[]}` (ranked chunks) |
| GET | `/health` | — | `{status, elasticsearch, qdrant}` |

## Demo (Streamlit)

A decoupled Streamlit page showcases the tech stack, **live architecture diagrams**, an
interactive **multi-agent chat**, and a **hybrid-retrieval inspector**. It talks to the FastAPI
backend over HTTP.

```bash
make up         # (or make serve) start the backend (ES + Qdrant + API)
make demo       # Streamlit at http://localhost:8501
```

Set `API_URL` to point the page at a non-default backend (default `http://localhost:8000`). The
overview/architecture sections render without a backend; chat and the retrieval inspector show a
status banner if the API is unreachable.

## Evaluation

`make eval` compares hybrid retrieval against single-store baselines (see
[`docs/eval-report.md`](docs/eval-report.md)):

| Method | Recall@5 | MRR |
|---|---|---|
| es_only (BM25 + kuromoji) | 1.000 | 0.833 |
| qdrant_only (BGE-m3 dense) | 1.000 | 1.000 |
| **hybrid (RRF + rerank)** | **1.000** | **0.929** |

On this small corpus dense retrieval already saturates rank-1, so hybrid does not beat it here;
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
| State | LangGraph SQLite checkpointer |
| API | FastAPI (+ SSE) |
| Packaging | Poetry, Docker, docker-compose |

## Project structure

```
core/        config (pydantic-settings), DeepSeek LLM factory, language detection
rag/         chunking, embeddings, es_store, qdrant_store, hybrid (RRF), rerank, retriever, ingest
tools/       tax / visa / ward_office calculators + domain-scoped knowledge tool
agents/      state, prompts, supervisor, handoffs, specialists/, graph, output
app/         FastAPI: schemas, routes (/chat, /chat/stream, /search, /health), main (lifespan)
knowledge/   bilingual markdown knowledge base (tax / visa / ward_office)
eval/        metrics (recall@k, MRR) + hybrid-vs-baseline harness + datasets
docker/      custom ElasticSearch image (kuromoji)
streamlit_app.py   decoupled Streamlit demo UI (overview, chat, retrieval inspector)
```

## Testing & CI

```bash
make test        # 68 unit tests, no services or API key required
make test-all    # + integration tests (real ES/Qdrant, model downloads, DEEPSEEK_API_KEY)
```

GitHub Actions runs the unit suite on every push/PR (`.github/workflows/ci.yml`). Integration
tests skip automatically when `DEEPSEEK_API_KEY` / services are absent.

## Roadmap

- More domains (banking, employment, housing, health/pension).
- Streamlit demo UI.
- Postgres checkpointer + auth/rate-limiting for production.
- Retrieval observability (latency, hit distribution) and answer-faithfulness eval.

## Notes

`DEEPSEEK_API_KEY` lives only in the git-ignored `.env` and is read at runtime (never baked into
the image). This is a learning/portfolio project; tool outputs are estimates and not legal or
tax advice.
