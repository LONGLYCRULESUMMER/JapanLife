# JapanLife Knowledge-Base Production-Scale Expansion Design

- **Date**: 2026-06-23
- **Status**: Approved for implementation planning
- **Author**: @coda1997 + Copilot
- **Scope**: Expand the RAG corpus from portfolio/demo size to a stronger small-production-style corpus while preserving the existing ingest and retrieval architecture.

---

## 1. Current State

JapanLife already has the end-to-end RAG and Agent architecture in place:

- `knowledge/` contains 50 Markdown documents across `tax`, `visa`, and `ward_office`.
- The corpus currently produces about 322 chunks.
- Each document is ingested by `rag/ingest.py`, chunked by `rag/chunking.py`, embedded with BGE-m3, then written to ElasticSearch and Qdrant.
- Retrieval evaluation has 95 cases across the three domains.
- The existing RAG code is sufficient for a larger corpus; the main limitation is corpus depth, topic breadth, and evaluation coverage.

The next step is a data expansion, not a retrieval rewrite.

---

## 2. Goal

Grow the knowledge base to a medium-size, credible RAG corpus:

- About **120 Markdown documents** total.
- About **800-1200 chunks** after ingest.
- Balanced coverage across `tax`, `visa`, and `ward_office`.
- More native Japanese documents, not only English documents queried by Japanese prompts.
- Expanded retrieval and answer evaluation so new content is measurable.

This scale is still manageable in the repository, but large enough that the project no longer reads as a toy 50-document demo.

---

## 3. Non-Goals

- Do not change the current chunking, embedding, ES, Qdrant, RRF, rerank, or Agent orchestration code.
- Do not build web crawlers or live official-site synchronization in this phase.
- Do not introduce a new database-backed manifest or incremental ingest mechanism in this phase.
- Do not claim legal, tax, immigration, or municipal advice. Content remains general information with official source links.

---

## 4. Recommended Approach

Use a **medium corpus expansion pack**:

1. Add about 70 new Markdown documents across the existing three domains.
2. Keep the current `knowledge/<domain>/*.md` convention so ingest automatically picks them up.
3. Use official or quasi-official source URLs in front-matter.
4. Prefer evergreen, high-frequency living-in-Japan topics.
5. Add retrieval cases for the new documents.
6. Add answer-level cases for important user-facing workflows.
7. Update docs/README statistics after measurement.

This approach gives the strongest resume impact for the least architectural risk: the RAG pipeline stays stable while the corpus and evaluation become materially more credible.

---

## 5. Content Expansion Shape

### Tax

Add documents around:

- employment income and withholding
- resident tax edge cases
- freelance bookkeeping
- blue return details
- invoice system details
- pension lump-sum tax reclaim
- overseas dependents
- housing loan deduction
- donation deduction
- tax payment methods and late penalties
- NISA/iDeCo high-level tax treatment
- crypto and side income overview
- company employee vs sole proprietor tax flow
- documents needed for final return
- common mistakes for foreign residents

### Visa

Add documents around:

- Engineer/Specialist in Humanities/International Services
- Intra-company transferee
- Specified Skilled Worker
- business manager status
- start-up visa overview
- family stay details
- spouse status after divorce
- permanent residency failure reasons
- points calculation examples
- renewal document preparation
- employer change notification
- side work and status restrictions
- COE process
- short-term stay limitations
- overstaying and special permission overview

### Ward Office

Add documents around:

- address change within the same city
- moving out abroad
- national health insurance premium basics
- premium reduction/exemption
- long-term care insurance
- maternity and childbirth support
- daycare application basics
- school enrollment for children
- child medical subsidy
- water/sewer setup
- bicycle registration and parking
- pet registration
- disability certificate overview
- public housing overview
- local consultation counters for foreign residents

### Native Japanese Documents

Increase native Japanese coverage for high-frequency topics. The priority is not literal translation; it is natural Japanese content that improves Japanese BM25/kuromoji recall and multilingual dense retrieval.

---

## 6. Data Model and File Format

Every new document uses the existing Markdown front-matter format:

```markdown
---
doc_title: Human-readable title
source_url: https://official-or-quasi-official-source.example/
language: en
last_updated: 2026-06-23
---

# Document Title

## Section

Content...
```

Required metadata:

- `doc_title`: used for citation display.
- `source_url`: used for traceability.
- `language`: `en` or `ja`.
- `last_updated`: date of the repository content update.

The ingest code derives:

- `domain` from the parent directory.
- `doc_id` from `domain/filename`.
- `section_path` from Markdown headings.
- `chunk_index` during chunking.
- `chunk_id` from `doc_id + section_path + chunk_index`.

---

## 7. Evaluation Expansion

Each new important document receives at least one retrieval case in:

- `eval/datasets/tax.jsonl`
- `eval/datasets/visa.jsonl`
- `eval/datasets/ward_office.jsonl`

Evaluation cases must continue using:

- `question`
- `relevant`
- `lang`
- `type`

Answer-level cases in `eval/datasets/answer_cases.jsonl` should cover workflows that require routing, language matching, disclaimer behavior, or multi-domain reasoning.

The target evaluation size is:

- Retrieval eval: about **180-220 cases** total.
- Answer eval: about **40-50 cases** total.

---

## 8. Validation

Implementation must verify:

1. All new Markdown documents have valid front-matter.
2. All retrieval `relevant` doc IDs point to real files.
3. Dataset integrity tests pass.
4. The corpus count and approximate chunk count increase as expected.
5. README and eval docs report the new corpus size honestly.

The expected commands are:

```bash
poetry run pytest -q tests/test_eval_datasets.py tests/test_answer_eval.py
make test
```

If ES and Qdrant are available:

```bash
make ingest
make eval
```

---

## 9. Risks and Mitigations

| Risk | Mitigation |
|---|---|
| Incorrect legal/tax/visa claims | Use general informational wording, official source URLs, disclaimers, and avoid over-specific claims unless already present in reliable sources. |
| Corpus grows but quality stays shallow | Add workflow-oriented docs and eval cases, not only isolated glossary pages. |
| Japanese content becomes machine-translation-like | Write natural Japanese summaries for high-frequency procedures. |
| Existing retrieval metrics drop because the corpus is larger | Run retrieval eval and report results honestly; use rerank + RRF as already designed. |
| Manual expansion becomes hard to maintain | Keep file naming, front-matter, and evaluation conventions strict. |

---

## 10. Implementation Boundary

This phase is a repository data expansion:

- Create new Markdown knowledge documents.
- Modify evaluation JSONL files.
- Update documentation statistics.
- Do not modify application code unless validation reveals a direct bug in existing data handling.

