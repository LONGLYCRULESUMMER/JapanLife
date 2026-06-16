# Architecture — a `/chat` request, end to end

This document traces one question through JapanLife, from the HTTP boundary down to
retrieval and back, and names the moving parts so the system can be explained in an
interview without hand-waving.

> Scope: this is a learning/portfolio project. Tool outputs and knowledge are demo-grade,
> not legal or tax advice.

## 10,000-foot view

```
client ──POST /chat──▶ FastAPI ──▶ LangGraph (supervisor → specialist) ──▶ answer + citations
                                          │
                                          ├─ deterministic @tool calls (calculators, checklists)
                                          └─ search_knowledge_base ──▶ Hybrid RAG (ES + Qdrant → RRF → rerank)
```

- **API layer** — `app/` (FastAPI): request/response schemas, routing, SSE streaming,
  conversation history, async ingest jobs, health.
- **Agent layer** — `agents/` (LangGraph): a supervisor that routes to one of three
  ReAct specialists (`tax` / `visa` / `ward_office`), with specialist→specialist handoff.
- **Tooling** — `tools/`: deterministic domain calculators/checklists + a domain-scoped
  knowledge-search tool.
- **Retrieval** — `rag/`: chunking, embeddings, ElasticSearch (BM25 + kuromoji), Qdrant
  (BGE-m3 dense), RRF fusion, cross-encoder rerank, plus caching.
- **Shared** — `core/`: settings, the DeepSeek LLM factory, language detection.

## Step by step: `POST /chat {"message": "...", "thread_id"?: "..."}`

1. **Request hits `app/routes.py:chat`.** A `thread_id` is taken from the body or
   generated. The initial graph state is built:
   `{messages: [HumanMessage], user_language: "", active_domain: None, citations: []}`.

2. **`graph.invoke(state, config={thread_id, recursion_limit})`.** The compiled
   LangGraph (`agents/graph.py`) runs. A SQLite checkpointer (`langgraph-checkpoint-sqlite`)
   persists state per `thread_id`, which is what makes multi-turn history and conversation
   restore work.

3. **Supervisor routes (`agents/supervisor.py`).** The supervisor uses the DeepSeek model
   with **structured output** (`Route` pydantic model: `tax|visa|ward_office|FINISH`).
   A deterministic backstop short-circuits to `END` once the last message is an
   `AIMessage`, guaranteeing termination even if the model never emits `FINISH`.

4. **Specialist runs (ReAct loop, `agents/specialists/*.py`).** The chosen specialist is a
   tool-calling agent. It decides, per turn, whether to:
   - call a **deterministic tool** (e.g. `visa_renewal_checklist`,
     `days_until_move_in_deadline`, income-tax / furusato-nozei estimators) for numbers and
     checklists, or
   - call **`search_knowledge_base`** for grounded prose.
   The specialist prompt instructs it to answer in the user's language and to cite sources.

5. **Knowledge search → Hybrid RAG (`rag/retriever.py`).** `search_knowledge_base` calls
   `HybridRetriever.search(query, domain)`:
   - (optional) **retrieval cache** check — `(query, domain, top_k)` with short TTL.
   - **ElasticSearch** BM25 over `content` + `content.ja` (kuromoji analyzer) — sparse/lexical.
   - **Qdrant** dense search over BGE-m3 embeddings (`embed_query`, itself embedding-cached).
   - **RRF fusion** (`rag/hybrid.py`) merges the two ranked lists (k = 60).
   - **Cross-encoder rerank** (`bge-reranker-v2-m3`, `rag/rerank.py`) reorders the fused set,
     returning the top N as `RetrievedChunk`s with a human-readable `citation`
     (`doc_title | section_path | source_url`).
   - **Graceful degradation**: if ES or Qdrant throws, the retriever logs and falls back to
     the other store instead of failing the request.

6. **Specialist composes the answer.** The tool result comes back as a `ToolMessage`
   containing context **and** a `Sources:` block. The model writes the final answer; the
   `Sources:` lines are what the API extracts as citations.

7. **Back through the supervisor → `END`.** The supervisor's backstop sees the specialist's
   `AIMessage` and finishes.

8. **Response assembled (`agents/output.py`).** `extract_reply` returns the last non-empty
   AI message; `extract_citations` pulls citation lines out of the knowledge-tool
   `ToolMessage`s. The API returns:
   `{reply, citations[], thread_id, route}` (`route` = `active_domain`).

## Streaming variant: `POST /chat/stream`

Same graph, but `graph.stream(..., stream_mode="messages", subgraphs=True)`. `subgraphs=True`
is required so tokens generated **inside** the specialist subgraph surface (not just
top-level nodes). The endpoint emits Server-Sent Events:

- `route` — which specialist was chosen (derived from the streaming namespace),
- `tool` — a tool step ran (the client resets any preamble text),
- `token` — an incremental answer-token delta,
- `done` — final event with `thread_id` and citations (or `error`).

## State, identity, and history

Identity is the LangGraph `thread_id` + checkpointer — not an ad-hoc message store. The
`/conversations*` endpoints read the checkpointer's SQLite tables to list, restore, and
delete past threads, reconstructing display turns with `reconstruct_messages`.

## Where to change things

| Want to change… | Touch… |
|---|---|
| The LLM provider | `core/llm.py` (single factory) |
| Routing behavior | `agents/supervisor.py`, `agents/prompts.py` |
| A specialist's tools | `tools/*_tools.py`, `agents/specialists/*.py` |
| Retrieval fusion / rerank | `rag/hybrid.py`, `rag/rerank.py`, `rag/retriever.py` |
| Chunking strategy | `rag/chunking.py` |
| Caching behavior | `rag/cache.py` + `core/config.py` toggles |
| Ingest as a job | `app/jobs.py`, `app/routes.py` (`/admin/ingest`) |
