# Backend Engineering Notes

The parts of JapanLife that make it a *backend* project rather than a prompt demo: caching,
background jobs, error handling, graceful degradation, and a clear story for what would come
next in production. Everything here is deliberately small enough to explain end-to-end.

## Caching (`rag/cache.py`)

Two caches sit on the hot path, both **gated by settings** and **no-ops when disabled**, so
behavior is unchanged unless explicitly turned on.

### Embedding cache (persistent)

- **Why**: BGE-m3 embedding is the dominant cost for repeated queries and for re-ingesting an
  unchanged corpus. Identical text should be embedded once.
- **What**: `SqliteKVCache` (a tiny string KV store) wrapped by `EmbeddingCache`, keyed by
  `sha256(model + text)`. The model id is part of the key, so switching embedding models can't
  return stale vectors.
- **Where**: `rag/embeddings.embed_texts` consults the cache and only calls the encoder for
  **misses**, then writes the new vectors back.
- **Config**: `ENABLE_EMBEDDING_CACHE` (default on), `EMBEDDING_CACHE_PATH`.

### Retrieval cache (short TTL, in-memory)

- **Why**: bursts of identical `(query, domain, top_k)` lookups (demo clicks, retries) would
  otherwise re-run BM25 + dense search + the cross-encoder rerank every time.
- **What**: `TTLCache`, a `threading.Lock`-guarded dict with per-entry expiry. The clock is
  injectable, which makes expiry deterministically testable.
- **Where**: `HybridRetriever.search` checks the cache before hitting the stores and writes the
  reranked result back.
- **Config**: `ENABLE_RETRIEVAL_CACHE` (default off — opt-in), `CACHE_TTL_SECONDS` (default 60).

### Swappability

Both caches expose a `get`/`set` interface (`KVCache` for embeddings). Moving to Redis is a
matter of providing a Redis-backed `KVCache`/TTL store behind the same methods — callers don't
change. This is the "clear, testable, replaceable" bar, not a premature distributed cache.

### Concurrency stance (be honest in interviews)

This is a **single-process** design. `SqliteKVCache` and `TTLCache` guard their state with a
`Lock`, which is correct under FastAPI's threadpool. It is **not** a cross-process cache: two
uvicorn workers would each have their own `TTLCache`, and SQLite is fine for a shared embedding
cache but isn't a high-write store. For multi-replica deployments, move both behind Redis.

## Async ingest jobs (`app/jobs.py`, `app/routes.py`)

Ingestion (chunk → embed → index into ES + Qdrant) is slow and needs no user interaction, so it
is modeled as a fire-and-forget job instead of blocking a request.

- `JobRegistry` — a `Lock`-guarded in-memory map of `Job`s. Each job tracks
  `id, status, created_at, started_at, finished_at, error, chunks_indexed`.
- `JobRegistry.run` runs the ingest function, recording the lifecycle and **never raising** —
  failures are captured on the job so the API can report them.
- Endpoints:
  - `POST /admin/ingest` → creates a job, schedules `registry.run` via FastAPI
    `BackgroundTasks`, returns `202` + the job.
  - `GET /admin/ingest/jobs` → list (most recent first).
  - `GET /admin/ingest/jobs/{id}` → one job, `404` if unknown.
- **Testable without infra**: the ingest callable is an injected dependency
  (`get_ingest_fn`), so tests submit a fake that returns a count or raises — no ES/Qdrant
  needed.

```bash
make serve            # start the API
make ingest-job-demo  # POST a job, then poll its status
```

### What this is not

`BackgroundTasks` runs in the same process and does not survive a restart or give you retries,
scheduling, or fan-out. The job model is shaped so the registry + endpoints stay the same when
the executor becomes Celery/RQ/Arq with a database-backed job table.

## Error handling & graceful degradation

- **Retrieval degradation** — if ElasticSearch *or* Qdrant raises, `HybridRetriever.search`
  logs a warning and continues with whatever store is healthy, so a single dependency outage
  degrades quality instead of taking down `/chat`.
- **Chat failures** — `/chat` wraps `graph.invoke` and returns `503` with a friendly message
  (full traceback logged, not leaked). `/chat/stream` emits an `error` SSE event instead of a
  broken stream.
- **Health** — `GET /health` probes ES and Qdrant and reports `ok` / `degraded` with
  per-dependency booleans.
- **Termination safety** — the supervisor has a deterministic backstop to `END` and the graph
  runs with a `recursion_limit`, so a misbehaving model can't loop forever.
- **Conversation endpoints** — listing/restoring tolerate malformed or missing state rather
  than 500-ing the whole list.

## Configuration

All knobs live in `core/config.py` (`pydantic-settings`), reading from env / `.env`. Secrets
(`DEEPSEEK_API_KEY`) live only in the git-ignored `.env` and are read at runtime — never baked
into the image. New cache knobs are documented in `.env.example`.

## Observability — the honest TODO list

Today: structured-ish logging via the stdlib `logging` module and the `/health` probe. Not yet
built, in rough priority order:

1. **Request metrics** — latency and error rate per endpoint; retrieval latency split across
   ES / Qdrant / rerank; cache hit/miss counters for both caches.
2. **Tracing** — OpenTelemetry spans across supervisor → specialist → tool → retriever to see
   where a slow `/chat` spends its time.
3. **Retrieval analytics** — hit distribution per document, queries with empty/low-score
   results (content-gap detection), per-`type` recall from the eval set over time.
4. **Answer-quality monitoring** — sample live answers through `eval/answer_metrics` (with the
   `LLMJudge`) to catch citation/grounding regressions.
5. **Production hardening** — Postgres checkpointer, auth + rate limiting on `/admin/*`, Redis
   caches, and a durable job queue.
