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
