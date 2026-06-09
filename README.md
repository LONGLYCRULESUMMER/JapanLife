# JapanLife

Hybrid-RAG multi-agent assistant for foreigners living in Japan.

## Plan 1: Retrieval foundation

A hybrid retrieval pipeline: markdown knowledge is chunked and indexed into both
**ElasticSearch** (BM25 + kuromoji Japanese analyzer) and **Qdrant** (BGE-m3 dense
vectors). Queries fan out to both stores, are fused with Reciprocal Rank Fusion, and
re-ranked with a `bge-reranker-v2-m3` cross-encoder.

```bash
make install        # install deps (Poetry)
make up             # start ElasticSearch (+kuromoji) and Qdrant via docker compose
make ingest         # chunk knowledge/ and index into both stores
make eval           # hybrid vs es-only / qdrant-only retrieval metrics (Recall@K, MRR)
make test           # unit tests (no services needed)
make test-all       # include integration tests (needs services + model downloads)
```

### Architecture

```
query ─▶ embed (BGE-m3) ─┬─▶ Qdrant  (dense / semantic)   ─┐
                         └─▶ ElasticSearch (BM25 + kuromoji)─┴─▶ RRF fuse ─▶ cross-encoder rerank ─▶ cited chunks
```

Each module has one responsibility: `rag/chunking.py` (section-aware splitting),
`rag/embeddings.py` (BGE-m3), `rag/qdrant_store.py`, `rag/es_store.py`,
`rag/hybrid.py` (Reciprocal Rank Fusion), `rag/rerank.py`, `rag/retriever.py`
(`HybridRetriever` + `search_knowledge_base`, with graceful degradation if one
store is down). `rag/ingest.py` indexes `knowledge/` into both stores.

### Verification (local)

- 30 tests pass (27 unit + 3 integration).
- kuromoji tokenizes `確定申告` → `["確定", "申告"]`.
- Ingested 74 chunks from 11 documents (tax / visa / ward_office).
- Retrieval metrics on the 7-question eval set (`make eval`):

  | method | Recall@5 | MRR |
  |---|---|---|
  | es_only (BM25) | 1.000 | 0.833 |
  | qdrant_only (dense) | 1.000 | 1.000 |
  | hybrid (RRF + rerank) | 1.000 | 0.929 |

  On this small, semantically-easy corpus dense retrieval already saturates rank-1,
  so hybrid does not beat it here. Hybrid's advantage shows on larger corpora and
  rare-term / exact-match queries (proper nouns, numbers, Japanese terms) where BM25
  complements dense recall. Metrics are reported as-is rather than tuned to win.

