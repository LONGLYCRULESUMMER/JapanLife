# RAG Evaluation — retrieval eval vs answer eval

JapanLife evaluates two different things, and it is worth being precise about which is
which, because they answer different questions and fail in different ways.

| | **Retrieval eval** | **Answer eval** |
|---|---|---|
| Question it answers | "Did we fetch the right document?" | "Was the produced answer good?" |
| Runner | `eval/run_eval.py` (`make eval`) | `eval/run_answer_eval.py` (`make answer-eval`) |
| Needs services | ES + Qdrant (ingested) | LLM agent **or** offline `--stub` |
| Needs API key | no | only for the real agent; otherwise skips/stub |
| Metrics | Recall@5, MRR | citation present/supported, disclaimer, language, route |
| Dataset | `eval/datasets/{tax,visa,ward_office}.jsonl` | `eval/datasets/answer_cases.jsonl` |

The two are intentionally decoupled. Retrieval can be perfect while the answer is bad
(model ignores context), and the answer can be acceptable while retrieval is mediocre
(model already knows the fact). Measuring both separates "search quality" from
"generation quality".

## Retrieval eval

### Dataset format (`{domain}.jsonl`)

```json
{"question": "確定申告の期間はいつからいつまでですか", "relevant": ["tax/01-tax-filing-overview.md"], "lang": "ja", "type": "numeric"}
```

- `relevant` — list of **document ids** (`doc_id = domain/filename`). A case is a hit if any
  relevant doc appears in the top results; cross-domain cases list more than one.
- `lang` — `en` / `ja` / `mixed` (the corpus and queries are bilingual).
- `type` — `keyword` / `semantic` / `numeric` / `cross` / `confusing`. Used for composition
  reporting and to make sure the suite isn't all easy keyword lookups.

The suite currently has **66 cases** (22 per domain). `run_eval.py` loads the three domain
files **by name** (not a glob), so adding other datasets — like `answer_cases.jsonl` — to
`eval/datasets/` never pollutes retrieval scoring.

### Metrics (`eval/metrics.py`)

- **Recall@k** — fraction of relevant docs found in the top `k` (here `k = 5`).
- **MRR** — mean reciprocal rank of the first relevant doc.

Both are computed at the **document** level (`doc_id`), deduplicating chunks from the same
document first (`_doc_ids`).

### Reproduce

```bash
make up && make ingest   # start ES + Qdrant and index knowledge/
make eval                # prints dataset composition + es_only / qdrant_only / hybrid
```

`run_eval.py` first prints the dataset composition (counts by language and query type), then
compares three strategies on the same questions: `es_only`, `qdrant_only`, and `hybrid`
(RRF + rerank). See [`eval-report.md`](eval-report.md) for the latest numbers and an honest
reading of them.

## Answer eval

Answer eval scores the **agent's answers** against expectations. It is built so it can run
in three modes without ever failing CI:

- `make answer-eval` — uses the real LangGraph agent if `DEEPSEEK_API_KEY` is set;
  otherwise prints a skip message and exits 0.
- `make answer-eval-stub` — fully offline. A deterministic `StubAnswerer` stands in for the
  LLM + retrieval stack, so the metric pipeline runs with no key and no services.

### Dataset format (`answer_cases.jsonl`)

```json
{"question": "How is resident tax calculated and when is it billed?", "expected_route": "tax", "expects_disclaimer": true, "lang": "en"}
```

- `expected_route` — the domain the supervisor should pick (`str`, or a list for
  legitimately cross-domain questions).
- `expects_disclaimer` — whether this is a high-risk (tax / legal / visa) question that
  should carry a disclaimer or "consult an official/professional".

### Metrics (`eval/answer_metrics.py`)

Each is a small, dependency-free function (so the harness runs offline):

- **`citation_present`** — did the answer carry at least one non-empty citation?
- **`citation_supported`** — is the answer grounded in the retrieved context? Default is a
  token-overlap heuristic (ASCII words + CJK bigrams). It is pluggable: pass an `LLMJudge`
  (also provided) to grade with a model instead. The heuristic keeps CI offline and fast.
- **`refusal_or_disclaimer`** — does the answer include a disclaimer / "consult"
  (EN + JA markers)? Aggregated as `disclaimer_compliance` over the cases that expect one.
- **`language_match`** — is the answer in the same language as the question
  (via `core.i18n.detect_language`)?
- **`route_correct`** — did routing match `expected_route` (string or membership)?

### Reproduce

```bash
make answer-eval-stub          # offline demo, all metrics, no key/services
make answer-eval               # real agent (needs DEEPSEEK_API_KEY + ingested stores)
```

Example offline output:

```
=== Answer evaluation (stub) — 15 cases ===
  citation_present       1.000
  citation_supported     1.000
  refusal_or_disclaimer  1.000
  language_match         1.000
  route_correct          0.933
  disclaimer_compliance  1.000
```

The stub is intentionally well-behaved on most metrics; `route_correct < 1.0` shows the
metric discriminating (its keyword router mis-routes one case), which is the point — the
harness, not the stub, is what's being demonstrated.

## Extending the datasets

- Add a knowledge doc under `knowledge/<domain>/` (front-matter optional but recommended).
- Add retrieval cases to `{domain}.jsonl` whose `relevant` ids point at real files —
  `tests/test_eval_datasets.py` enforces this (≥20/domain, valid langs, ids exist on disk).
- Add answer cases to `answer_cases.jsonl` with the expected route and disclaimer flag.
