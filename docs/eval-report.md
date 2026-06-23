# Evaluation Report

JapanLife is evaluated on two axes — **retrieval** (did we fetch the right document?) and
**answers** (was the produced answer good?). See [`rag-evaluation.md`](rag-evaluation.md) for
the full design; this page records the latest results.

## Corpus & datasets

- **Knowledge base**: 144 documents (tax 47, visa 48, ward_office 49; 33 native-Japanese docs)
  → 793 chunks after header-aware chunking. All documents carry front-matter with a real official
  or municipal `source_url` (ISA, NTA, MHLW, Soumu, Japan Pension Service, city sources, etc.).
- **Retrieval eval set**: **190 cases** (tax 64, visa 63, ward_office 63) in
  `eval/datasets/{domain}.jsonl`.
  Composition:
  - by language — en 120, ja 67, mixed 3
  - by type — semantic 62, numeric 44, keyword 43, cross-domain 21, confusing 20
- **Answer eval set**: 46 cases in `eval/datasets/answer_cases.jsonl` (with `expected_route`
  and `expects_disclaimer`).

## Retrieval eval

Method (`eval/run_eval.py`, `make eval`): for each question we record the relevant
**documents** (`doc_id = domain/filename`) and measure, at the document level:

- **Recall@5** — is a relevant document in the top 5 retrieved?
- **MRR** — mean reciprocal rank of the first relevant document.

Three strategies are compared on the same questions: `es_only` (BM25 + kuromoji),
`qdrant_only` (BGE-m3 dense), and `hybrid` (RRF, k=60, + `bge-reranker-v2-m3`).

### Results

The numbers below were measured on the **earlier 11-document / 7-question** corpus and are
retained for reference:

| Method | Recall@5 | MRR |
|---|---|---|
| es_only (BM25 + kuromoji) | 1.000 | 0.833 |
| qdrant_only (BGE-m3 dense) | 1.000 | 1.000 |
| **hybrid (RRF + rerank)** | **1.000** | **0.929** |

> NOTE: These predate the current corpus/dataset expansion (144 docs, 190 cases). They are **not**
> re-stated for the new corpus because regenerating them requires running ES + Qdrant and
> downloading the embedding/reranker models, which isn't done in CI. To regenerate on the
> current corpus:
>
> ```bash
> make up && make ingest && make eval
> ```
>
> `make eval` prints the dataset composition followed by the three-strategy table. Report
> whatever it prints — the harness is built to be run, not tuned to win.

### Interpretation (honest)

On a small, semantically straightforward corpus every method already retrieves the relevant
document within the top 5, and dense retrieval saturates rank-1, so **hybrid does not beat
strong dense retrieval here**. The value of hybrid + BM25/kuromoji shows up at scale and on
rare-term / exact-match queries (proper nouns, numbers, specific Japanese terms such as
確定申告 or マイナンバー). The expanded 190-case set deliberately adds numeric, cross-domain,
and confusable queries so this effect has room to appear as the corpus grows.

## Answer eval

Method (`eval/run_answer_eval.py`). Real-agent mode needs `DEEPSEEK_API_KEY` + ingested
stores; the offline `--stub` mode exercises the full metric pipeline with no key or services.

Offline stub run (`make answer-eval-stub`, 46 cases) — demonstrates the metrics, not model
quality:

| Metric | Rate |
|---|---|
| citation_present | 1.000 |
| citation_supported | 1.000 |
| refusal_or_disclaimer | 1.000 |
| language_match | 1.000 |
| route_correct | 0.870 |
| disclaimer_compliance | 1.000 |

`route_correct = 0.870` is expected: the stub's tiny keyword router is intentionally simple and
mis-routes several expanded cases. That the number is below 1.0 is the point — it shows the metric discriminating. To run
the **real** agent instead:

```bash
make answer-eval     # uses DEEPSEEK_API_KEY if set; otherwise skips gracefully
```

## Reproduce everything

```bash
make up && make ingest    # ES + Qdrant + index knowledge/
make eval                 # retrieval: composition + es/qdrant/hybrid table
make answer-eval-stub     # answer metrics, fully offline
make answer-eval          # answer metrics with the real agent (needs API key)
```
