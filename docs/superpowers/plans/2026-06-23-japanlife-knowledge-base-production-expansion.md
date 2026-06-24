# JapanLife Knowledge Base Production Expansion Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Expand JapanLife's knowledge base from 50 demo-sized documents to a medium corpus of about 120 documents with matching retrieval and answer evaluation coverage.

**Architecture:** This is a data-only expansion. Keep the existing `knowledge/<domain>/*.md` file convention, front-matter schema, ingest pipeline, ES/Qdrant stores, RRF fusion, reranker, and Agent tools unchanged. Add new Markdown knowledge documents, extend JSONL evaluation datasets, and update documentation statistics after measuring the final corpus.

**Tech Stack:** Markdown front-matter, JSONL eval datasets, Poetry, pytest, existing `rag.ingest`/`rag.chunking` pipeline.

---

## File Structure

| File(s) | Responsibility |
|---|---|
| `knowledge/tax/14-*.md` through `knowledge/tax/36-*.md` | Add 23 English tax documents. |
| `knowledge/tax/*.ja.md` | Add 8 native Japanese tax documents for frequent topics. |
| `knowledge/visa/15-*.md` through `knowledge/visa/37-*.md` | Add 23 English visa/immigration documents. |
| `knowledge/visa/*.ja.md` | Add 8 native Japanese visa documents for frequent topics. |
| `knowledge/ward_office/15-*.md` through `knowledge/ward_office/38-*.md` | Add 24 English municipal procedure documents. |
| `knowledge/ward_office/*.ja.md` | Add 8 native Japanese ward-office documents for frequent topics. |
| `eval/datasets/{tax,visa,ward_office}.jsonl` | Add retrieval cases that point to the new doc IDs. |
| `eval/datasets/answer_cases.jsonl` | Add answer-level cases for new workflows and routing behavior. |
| `README.md`, `README.zh-CN.md`, `docs/eval-report.md`, `docs/rag-evaluation.md`, `docs/rag-evaluation.zh-CN.md` | Update corpus and eval statistics after measurement. |

---

## Task 1: Add English Tax Expansion Pack

**Files:** Create 23 Markdown documents under `knowledge/tax/`.

- [ ] **Step 1: Create the 23 English tax docs with front-matter**

Create these files. Each file must start with front-matter containing `doc_title`, `source_url`, `language: en`, and `last_updated: 2026-06-23`.

| File | Source URL | Required sections |
|---|---|---|
| `knowledge/tax/14-employment-income-withholding.md` | `https://www.nta.go.jp/english/taxes/individual/index.htm` | `# Employment Income and Withholding`, `## How withholding works`, `## Year-end adjustment`, `## When filing is still needed`, `## Tips for Foreign Residents` |
| `knowledge/tax/15-salary-vs-business-income.md` | `https://www.nta.go.jp/english/taxes/individual/index.htm` | `# Salary Income vs Business Income`, `## Salary income`, `## Business income`, `## Side income`, `## Practical classification tips` |
| `knowledge/tax/16-blue-return-details.md` | `https://www.nta.go.jp/taxes/shiraberu/taxanswer/shotoku/2070.htm` | `# Blue Return Details`, `## Benefits`, `## Bookkeeping requirements`, `## Application deadline`, `## Common mistakes` |
| `knowledge/tax/17-freelance-bookkeeping.md` | `https://www.nta.go.jp/english/taxes/individual/index.htm` | `# Bookkeeping for Freelancers`, `## Income and expenses`, `## Receipts`, `## Home office and utilities`, `## Retention period` |
| `knowledge/tax/18-invoice-system-freelancers.md` | `https://www.nta.go.jp/english/taxes/consumption_tax/index.htm` | `# Invoice System for Freelancers`, `## Qualified invoice issuer`, `## When registration matters`, `## Client-side implications`, `## Tips` |
| `knowledge/tax/19-tax-payment-methods.md` | `https://www.nta.go.jp/english/taxes/individual/index.htm` | `# How to Pay National Tax`, `## Bank and convenience store payment`, `## e-Tax and direct payment`, `## Credit card payment`, `## Keep proof of payment` |
| `knowledge/tax/20-late-filing-penalties.md` | `https://www.nta.go.jp/english/taxes/individual/index.htm` | `# Late Filing and Penalties`, `## Late filing surcharge`, `## Delinquent tax`, `## Voluntary correction`, `## Prevention tips` |
| `knowledge/tax/21-overseas-dependent-documents.md` | `https://www.nta.go.jp/english/taxes/individual/12011.htm` | `# Overseas Dependent Documents`, `## Relationship documents`, `## Remittance documents`, `## Translation needs`, `## Tips` |
| `knowledge/tax/22-housing-loan-deduction.md` | `https://www.nta.go.jp/english/taxes/individual/index.htm` | `# Housing Loan Deduction`, `## Basic idea`, `## First-year tax return`, `## Later year-end adjustment`, `## Foreign resident notes` |
| `knowledge/tax/23-donation-deductions.md` | `https://www.nta.go.jp/english/taxes/individual/index.htm` | `# Donation Deductions`, `## Eligible donations`, `## Furusato nozei vs other donations`, `## How to claim`, `## Receipt handling` |
| `knowledge/tax/24-nisa-overview.md` | `https://www.fsa.go.jp/policy/nisa2/index.html` | `# NISA Overview`, `## Tax-free investment idea`, `## Growth and tsumitate investment枠`, `## Not a deduction`, `## Resident notes` |
| `knowledge/tax/25-ideco-overview.md` | `https://www.mhlw.go.jp/stf/seisakunitsuite/bunya/0000192886.html` | `# iDeCo Tax Overview`, `## Contribution deduction`, `## Investment gains`, `## Receiving benefits`, `## Eligibility notes` |
| `knowledge/tax/26-crypto-tax-overview.md` | `https://www.nta.go.jp/english/taxes/individual/index.htm` | `# Crypto Tax Overview`, `## Miscellaneous income`, `## Taxable events`, `## Record keeping`, `## Caution` |
| `knowledge/tax/27-stock-capital-gains.md` | `https://www.nta.go.jp/english/taxes/individual/index.htm` | `# Stock Capital Gains`, `## Separate taxation`, `## Withholding accounts`, `## Foreign broker issues`, `## Loss carryforward` |
| `knowledge/tax/28-pension-lump-sum-tax-reclaim.md` | `https://www.nenkin.go.jp/international/japanese-system/withdrawalpayment/payment.html` | `# Pension Lump-Sum Tax Reclaim`, `## Lump-sum withdrawal`, `## Withholding tax`, `## Tax representative`, `## Timeline` |
| `knowledge/tax/29-resident-tax-moving-year.md` | `https://www.soumu.go.jp/main_sosiki/jichi_zeisei/czaisei/czaisei_seido/kojin.html` | `# Resident Tax in Moving Years`, `## January 1 rule`, `## Moving within Japan`, `## Leaving Japan`, `## Payment reminders` |
| `knowledge/tax/30-tax-certificates.md` | `https://www.soumu.go.jp/main_sosiki/jichi_gyousei/c-gyousei/` | `# Tax Certificates`, `## Income certificate`, `## Tax payment certificate`, `## Where to request`, `## Visa and PR use` |
| `knowledge/tax/31-documents-for-final-return.md` | `https://www.nta.go.jp/english/taxes/individual/index.htm` | `# Documents for Final Tax Return`, `## Employment documents`, `## Deduction documents`, `## Foreign income documents`, `## Filing checklist` |
| `knowledge/tax/32-correction-amended-return.md` | `https://www.nta.go.jp/english/taxes/individual/index.htm` | `# Correcting a Tax Return`, `## Correction before deadline`, `## Amended return`, `## Claim for correction`, `## Tips` |
| `knowledge/tax/33-tax-office-consultation.md` | `https://www.nta.go.jp/english/index.htm` | `# Tax Office Consultation`, `## Where to ask`, `## What to bring`, `## Interpretation limits`, `## When to use a tax accountant` |
| `knowledge/tax/34-common-tax-mistakes.md` | `https://www.nta.go.jp/english/taxes/individual/index.htm` | `# Common Tax Mistakes`, `## Side income`, `## Overseas dependents`, `## Resident tax lag`, `## Missing documents` |
| `knowledge/tax/35-social-insurance-and-tax.md` | `https://www.mhlw.go.jp/english/` | `# Social Insurance and Tax`, `## Different systems`, `## Year-end adjustment documents`, `## Income walls`, `## Resident notes` |
| `knowledge/tax/36-tax-calendar.md` | `https://www.nta.go.jp/english/taxes/individual/index.htm` | `# Tax Calendar`, `## January to March`, `## June resident tax`, `## Year-end adjustment season`, `## Freelancer deadlines` |

- [ ] **Step 2: Verify tax front-matter and counts**

Run:

```bash
cd /Users/javagod/VsCodeProjects/JapanLife/.worktrees/knowledge-production-expansion
python3 - <<'PY'
from pathlib import Path
files = sorted(Path("knowledge/tax").glob("1[4-9]-*.md")) + sorted(Path("knowledge/tax").glob("2[0-9]-*.md")) + sorted(Path("knowledge/tax").glob("3[0-6]-*.md"))
assert len(files) == 23, len(files)
for f in files:
    text = f.read_text(encoding="utf-8")
    for key in ("doc_title:", "source_url:", "language: en", "last_updated: 2026-06-23"):
        assert key in text, (f, key)
print("tax English docs OK:", len(files))
PY
```

Expected: `tax English docs OK: 23`.

- [ ] **Step 3: Commit**

```bash
git add knowledge/tax/1[4-9]-*.md knowledge/tax/2[0-9]-*.md knowledge/tax/3[0-6]-*.md
git commit -m "data(knowledge): expand English tax corpus"
```

---

## Task 2: Add English Visa Expansion Pack

**Files:** Create 23 Markdown documents under `knowledge/visa/`.

- [ ] **Step 1: Create the 23 English visa docs**

Create `knowledge/visa/15-engineer-humanities-international-services.md`, `16-intra-company-transferee.md`, `17-specified-skilled-worker.md`, `18-business-manager-status.md`, `19-startup-visa-overview.md`, `20-certificate-of-eligibility.md`, `21-renewal-document-preparation.md`, `22-employer-change-notification.md`, `23-side-work-permission.md`, `24-family-stay-details.md`, `25-spouse-status-after-divorce.md`, `26-pr-failure-reasons.md`, `27-hsp-points-examples.md`, `28-short-term-stay-limitations.md`, `29-overstay-and-special-permission.md`, `30-changing-jobs-on-work-visa.md`, `31-remote-work-for-foreign-employers.md`, `32-student-attendance-and-renewal.md`, `33-dependent-child-schooling.md`, `34-long-term-resident-status.md`, `35-designated-activities-overview.md`, `36-application-status-and-special-period.md`, and `37-immigration-consultation.md`.

Each doc must use `language: en`, `last_updated: 2026-06-23`, an official `moj.go.jp` or `isa` source URL where possible, and 3-5 `##` sections that explain eligibility, process, documents, and cautions for foreign residents.

- [ ] **Step 2: Verify visa front-matter and counts**

Run:

```bash
cd /Users/javagod/VsCodeProjects/JapanLife/.worktrees/knowledge-production-expansion
python3 - <<'PY'
from pathlib import Path
files = sorted(Path("knowledge/visa").glob("1[5-9]-*.md")) + sorted(Path("knowledge/visa").glob("2[0-9]-*.md")) + sorted(Path("knowledge/visa").glob("3[0-7]-*.md"))
assert len(files) == 23, len(files)
for f in files:
    text = f.read_text(encoding="utf-8")
    for key in ("doc_title:", "source_url:", "language: en", "last_updated: 2026-06-23"):
        assert key in text, (f, key)
print("visa English docs OK:", len(files))
PY
```

Expected: `visa English docs OK: 23`.

- [ ] **Step 3: Commit**

```bash
git add knowledge/visa/1[5-9]-*.md knowledge/visa/2[0-9]-*.md knowledge/visa/3[0-7]-*.md
git commit -m "data(knowledge): expand English visa corpus"
```

---

## Task 3: Add English Ward-Office Expansion Pack

**Files:** Create 24 Markdown documents under `knowledge/ward_office/`.

- [ ] **Step 1: Create the 24 English ward-office docs**

Create `knowledge/ward_office/15-address-change-same-city.md`, `16-moving-out-abroad.md`, `17-national-health-insurance-premiums.md`, `18-nhi-reduction-exemption.md`, `19-long-term-care-insurance.md`, `20-maternity-childbirth-support.md`, `21-daycare-application-basics.md`, `22-school-enrollment-children.md`, `23-child-medical-subsidy.md`, `24-water-sewer-setup.md`, `25-bicycle-registration-parking.md`, `26-pet-registration.md`, `27-disability-certificate-overview.md`, `28-public-housing-overview.md`, `29-foreign-resident-consultation.md`, `30-multilingual-support.md`, `31-library-and-community-services.md`, `32-marriage-divorce-registration.md`, `33-death-registration.md`, `34-family-register-for-foreigners.md`, `35-notification-after-birth.md`, `36-tax-payment-at-city-office.md`, `37-my-number-card-renewal.md`, and `38-convenience-store-certificates.md`.

Each doc must use `language: en`, `last_updated: 2026-06-23`, an official ministry/municipal source URL where possible, and 3-5 `##` sections that explain who needs the procedure, where to apply, documents, deadlines, and foreign-resident notes.

- [ ] **Step 2: Verify ward-office front-matter and counts**

Run:

```bash
cd /Users/javagod/VsCodeProjects/JapanLife/.worktrees/knowledge-production-expansion
python3 - <<'PY'
from pathlib import Path
files = sorted(Path("knowledge/ward_office").glob("1[5-9]-*.md")) + sorted(Path("knowledge/ward_office").glob("2[0-9]-*.md")) + sorted(Path("knowledge/ward_office").glob("3[0-8]-*.md"))
assert len(files) == 24, len(files)
for f in files:
    text = f.read_text(encoding="utf-8")
    for key in ("doc_title:", "source_url:", "language: en", "last_updated: 2026-06-23"):
        assert key in text, (f, key)
print("ward-office English docs OK:", len(files))
PY
```

Expected: `ward-office English docs OK: 24`.

- [ ] **Step 3: Commit**

```bash
git add knowledge/ward_office/1[5-9]-*.md knowledge/ward_office/2[0-9]-*.md knowledge/ward_office/3[0-8]-*.md
git commit -m "data(knowledge): expand English ward-office corpus"
```

---

## Task 4: Add Native Japanese Expansion Pack

**Files:** Create 24 `.ja.md` documents: 8 tax, 8 visa, 8 ward-office.

- [ ] **Step 1: Create Japanese tax docs**

Create: `knowledge/tax/14-employment-income-withholding.ja.md`, `16-blue-return-details.ja.md`, `18-invoice-system-freelancers.ja.md`, `21-overseas-dependent-documents.ja.md`, `28-pension-lump-sum-tax-reclaim.ja.md`, `29-resident-tax-moving-year.ja.md`, `31-documents-for-final-return.ja.md`, `36-tax-calendar.ja.md`.

- [ ] **Step 2: Create Japanese visa docs**

Create: `knowledge/visa/15-engineer-humanities-international-services.ja.md`, `20-certificate-of-eligibility.ja.md`, `21-renewal-document-preparation.ja.md`, `22-employer-change-notification.ja.md`, `23-side-work-permission.ja.md`, `26-pr-failure-reasons.ja.md`, `30-changing-jobs-on-work-visa.ja.md`, `36-application-status-and-special-period.ja.md`.

- [ ] **Step 3: Create Japanese ward-office docs**

Create: `knowledge/ward_office/15-address-change-same-city.ja.md`, `16-moving-out-abroad.ja.md`, `17-national-health-insurance-premiums.ja.md`, `18-nhi-reduction-exemption.ja.md`, `20-maternity-childbirth-support.ja.md`, `21-daycare-application-basics.ja.md`, `35-notification-after-birth.ja.md`, `37-my-number-card-renewal.ja.md`.

Each Japanese doc must use `language: ja`, `last_updated: 2026-06-23`, natural Japanese prose, and the same source URL as its English counterpart.

- [ ] **Step 4: Verify Japanese docs**

Run:

```bash
cd /Users/javagod/VsCodeProjects/JapanLife/.worktrees/knowledge-production-expansion
python3 - <<'PY'
from pathlib import Path
files = [
*Path("knowledge/tax").glob("*.ja.md"),
*Path("knowledge/visa").glob("*.ja.md"),
*Path("knowledge/ward_office").glob("*.ja.md"),
]
new = [f for f in files if "last_updated: 2026-06-23" in f.read_text(encoding="utf-8")]
assert len(new) == 24, len(new)
for f in new:
    text = f.read_text(encoding="utf-8")
    assert "language: ja" in text, f
    assert "source_url:" in text, f
print("new Japanese docs OK:", len(new))
PY
```

Expected: `new Japanese docs OK: 24`.

- [ ] **Step 5: Commit**

```bash
git add knowledge/tax/*.ja.md knowledge/visa/*.ja.md knowledge/ward_office/*.ja.md
git commit -m "data(knowledge): add native Japanese expansion docs"
```

---

## Task 5: Expand Evaluation Datasets

**Files:** Modify `eval/datasets/tax.jsonl`, `eval/datasets/visa.jsonl`, `eval/datasets/ward_office.jsonl`, `eval/datasets/answer_cases.jsonl`.

- [ ] **Step 1: Add retrieval cases**

Add at least one retrieval case per new English doc and one Japanese case for each new `.ja.md` document. Use existing JSONL field names only: `question`, `relevant`, `lang`, and `type`.

- [ ] **Step 2: Add answer cases**

Add 15-25 answer cases covering new tax, visa, ward-office, and cross-domain workflows. Each case must include `question`, `expected_route`, `expects_disclaimer`, and `lang`.

- [ ] **Step 3: Run dataset tests**

Run:

```bash
cd /Users/javagod/VsCodeProjects/JapanLife/.worktrees/knowledge-production-expansion
poetry run pytest -q tests/test_eval_datasets.py tests/test_answer_eval.py
```

Expected: all tests pass.

- [ ] **Step 4: Commit**

```bash
git add eval/datasets/*.jsonl
git commit -m "eval: expand datasets for production-scale knowledge base"
```

---

## Task 6: Measure Corpus and Update Documentation

**Files:** Modify `README.md`, `README.zh-CN.md`, `docs/eval-report.md`, `docs/rag-evaluation.md`, `docs/rag-evaluation.zh-CN.md`.

- [ ] **Step 1: Measure corpus size**

Run:

```bash
cd /Users/javagod/VsCodeProjects/JapanLife/.worktrees/knowledge-production-expansion
poetry run python - <<'PY'
from rag.ingest import load_documents, build_chunks
docs = load_documents()
chunks = build_chunks(docs)
by_domain = {}
for domain, *_ in docs:
    by_domain[domain] = by_domain.get(domain, 0) + 1
print("docs", len(docs), by_domain)
print("chunks", len(chunks))
PY
```

Record the exact document and chunk counts in docs.

- [ ] **Step 2: Update documentation statistics**

Update the docs and README text that currently says 50 docs, 95 cases, and 322 chunks. Do not invent eval scores if `make eval` was not run; mark service-dependent metrics as pending rerun.

- [ ] **Step 3: Run tests**

Run:

```bash
cd /Users/javagod/VsCodeProjects/JapanLife/.worktrees/knowledge-production-expansion
poetry run pytest -q tests/test_eval_datasets.py tests/test_answer_eval.py
make test
```

Expected: all tests pass.

- [ ] **Step 4: Commit**

```bash
git add README.md README.zh-CN.md docs/eval-report.md docs/rag-evaluation.md docs/rag-evaluation.zh-CN.md
git commit -m "docs: update knowledge base scale after expansion"
```

---

## Self-Review

**Spec coverage:** The plan covers corpus growth, English breadth, native Japanese content, retrieval eval, answer eval, and documentation updates. It intentionally excludes ingest/retrieval code changes, matching the approved design.

**Placeholder scan:** The plan contains no TBD markers. The content generation tasks are bounded by exact filenames, source URLs or source policy, required sections, metadata, and validation commands.

**Type consistency:** JSONL field names match existing datasets: `question`, `relevant`, `lang`, `type`, `expected_route`, and `expects_disclaimer`.

