# JapanLife Knowledge-Base Enrichment Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking. **This is a content/data plan, not code TDD** — each task creates Markdown knowledge docs or JSONL eval cases and is verified by parse/word-count checks and the existing `tests/test_eval_datasets.py` integrity suite. No application code changes.

**Goal:** Grow the knowledge base from 26 docs / ~7.5k words to ~50 docs / ~18k words across tax/visa/ward_office — adding 15 English topic docs, 9 native-Japanese parallel docs, deepening the thinnest docs, fixing `language` front-matter, and expanding the retrieval + answer eval datasets to cover the new content.

**Architecture:** Pure data. `rag/ingest.py` globs `knowledge/*/*.md`; `domain = parent dir`, `doc_id = domain/filename`. `rag/chunking.py` splits by Markdown header then 1200-char windows (150 overlap) and is language-agnostic, so `*.ja.md` files ingest natively with `doc_id` like `tax/01-...ja.md`. Front-matter is simple `key: value` lines (`doc_title`, `source_url`, `language`, `last_updated`). Eval datasets are JSONL under `eval/datasets/`.

**Tech Stack:** Markdown + front-matter, JSONL, pytest (`tests/test_eval_datasets.py`, `tests/test_answer_eval.py`).

Reference spec: `docs/superpowers/specs/2026-06-19-japanlife-knowledge-base-enrichment-design.md`.

**Hard constraints (enforced by `tests/test_eval_datasets.py`):**
- Each domain JSONL keeps `≥ 20` cases; total `≥ 60`.
- Every `relevant` doc_id in a retrieval case **must resolve to a real file** → always create the doc before adding its eval case.
- Retrieval case `lang ∈ {en, ja, mixed}`; `type ∈ {keyword, semantic, numeric, cross, confusing}` (all five must appear across the suite — they already do; reuse these values).
- Answer cases (`answer_cases.jsonl`) need `question`, `expected_route` (string or list), `expects_disclaimer` (bool), `lang`.

**House style for docs** (match existing, e.g. `knowledge/tax/04-furusato-nozei.md`):
- Front-matter block first: `doc_title`, `source_url` (official gov/city site), `language`, `last_updated: 2025-06-01`.
- `#` H1 title with the Japanese term in （）, then `##` sections, bullet/▪ lists and Markdown tables.
- English docs: English prose with key Japanese terms in （）. Japanese docs: natural Japanese prose (not a literal translation).
- Approximate figures use the `~¥` style. End "foreigner-facing" docs with a short Tips/注意 section.
- Target 350–450 words per new doc.

---

## File Structure

| File(s) | Responsibility |
|---|---|
| `knowledge/tax/01..07-*.md` | **Modify** front-matter only — add `language: en` |
| `knowledge/tax/09..13-*.md` | **Create** 5 new English tax topic docs |
| `knowledge/visa/10..14-*.md` | **Create** 5 new English visa topic docs |
| `knowledge/ward_office/10..14-*.md` | **Create** 5 new English ward-office topic docs |
| `knowledge/{visa/01,visa/02,ward_office/01,ward_office/02}-*.md` | **Modify** — deepen thin docs |
| `knowledge/{tax,visa,ward_office}/NN-*.ja.md` | **Create** 9 native-Japanese parallel docs |
| `eval/datasets/{tax,visa,ward_office}.jsonl` | **Modify** — add retrieval cases for new docs |
| `eval/datasets/answer_cases.jsonl` | **Modify** — add answer cases for new topics |
| `README.md` | **Modify** — update "66 cases / 22 per domain" + doc-count language |

---

## Task 1: Front-matter hygiene — add `language: en` to 7 tax docs

**Files:** Modify `knowledge/tax/01..07-*.md` (front-matter only).

- [ ] **Step 1: Add the `language: en` line to each of the 7 tax docs**

For each file below, insert `language: en` into the front-matter block (after `source_url`, before `last_updated` if present, else before the closing `---`). The 7 files:
`01-tax-filing-overview.md`, `02-income-tax-brackets.md`, `03-deductions-guide.md`, `04-furusato-nozei.md`, `05-year-end-adjustment.md`, `06-etax-guide.md`, `07-tax-for-freelancers.md`.

Example (`knowledge/tax/04-furusato-nozei.md` head becomes):
```markdown
---
doc_title: Furusato Nozei Guide for Foreigners
source_url: https://www.soumu.go.jp/main_sosiki/jichi_zeisei/czaisei/czaisei_seido/furusato/
language: en
last_updated: 2025-01-15
---
```

- [ ] **Step 2: Verify every knowledge doc now has a `language` field**

Run:
```bash
cd /Users/javagod/VsCodeProjects/JapanLife && for f in knowledge/*/*.md; do grep -q "^language:" "$f" || echo "MISSING: $f"; done; echo "done"
```
Expected: prints only `done` (no `MISSING` lines).

- [ ] **Step 3: Commit**

```bash
git add knowledge/tax/0[1-7]-*.md
git commit -m "data(knowledge): add language: en front-matter to tax docs 01-07"
```

---

## Task 2: Breadth — 5 new English tax docs (09–13)

**Files:** Create `knowledge/tax/09-consumption-tax.md`, `10-dependents-deductions.md`, `11-medical-expense-deduction.md`, `12-tax-treaty-foreign-income.md`, `13-leaving-japan-tax.md`.

Each doc uses the house style. The concrete outline + facts for each:

- [ ] **Step 1: Create `knowledge/tax/09-consumption-tax.md`**

Front-matter: `doc_title: Consumption Tax (Shōhizei) Guide`, `source_url: https://www.nta.go.jp/english/taxes/consumption_tax/index.htm`, `language: en`, `last_updated: 2025-06-01`.
Sections & key content:
- `# Consumption Tax (消費税) in Japan` — intro: national + local consumption tax on most goods/services.
- `## Rates` — standard **10%**; reduced **8%** for food/non-alcoholic drinks (takeout/groceries) and newspapers (subscription, 2+/week). Table of examples (eat-in 10% vs takeout 8%).
- `## Tax-included vs tax-excluded pricing (税込/税抜)` — prices usually shown 税込 (incl.).
- `## Tax-free shopping for visitors (免税)` — only for short-term *visitors*, not residents; residents pay consumption tax.
- `## Consumption tax for businesses & freelancers` — taxable businesses; the **Invoice System (インボイス制度, qualified invoice)** from Oct 2023; small businesses under ¥10M base-period sales may be tax-exempt (免税事業者).
- `## Tips for Foreigners` — keep receipts; eat-in vs takeout difference; invoice number matters if you freelance.

- [ ] **Step 2: Create `knowledge/tax/10-dependents-deductions.md`**

Front-matter: `doc_title: Dependents and the Dependent Deduction`, `source_url: https://www.nta.go.jp/english/taxes/individual/12011.htm`, `language: en`, `last_updated: 2025-06-01`.
Sections & key content:
- `# Dependent Deduction (扶養控除)` — reduces taxable income for qualifying dependents.
- `## Who qualifies` — relatives you support, annual income ≤ ¥480,000 (or salary ≤ ¥1,030,000); the "¥1.03M wall".
- `## Deduction amounts` — general dependent ~¥380,000; specified dependent (19–22) ~¥630,000; elderly dependent amounts; spouse handled via **spouse deduction/special spouse deduction (配偶者控除/配偶者特別控除)**.
- `## Dependents living abroad (国外扶養親族)` — extra documentation (relationship + remittance proof) required.
- `## How to claim` — via year-end adjustment (年末調整) or tax return (確定申告).
- `## Tips for Foreigners` — keep remittance records for overseas family; the income walls (¥1.03M / ¥1.30M).

- [ ] **Step 3: Create `knowledge/tax/11-medical-expense-deduction.md`**

Front-matter: `doc_title: Medical Expense Deduction`, `source_url: https://www.nta.go.jp/english/taxes/individual/12013.htm`, `language: en`, `last_updated: 2025-06-01`.
Sections & key content:
- `# Medical Expense Deduction (医療費控除)` — deduct qualifying medical costs via tax return.
- `## Threshold` — expenses exceeding **¥100,000** (or 5% of income if income < ¥2M) are deductible, up to ¥2,000,000.
- `## What counts` — doctor/dentist, prescriptions, hospital transport; not cosmetic or general health supplements.
- `## Self-Medication tax system (セルフメディケーション税制)` — alternative for OTC switch-OTC drugs over ¥12,000 (can't combine with the regular one).
- `## How to claim` — must file 確定申告 (not year-end adjustment); attach a medical-expense statement (医療費控除の明細書); keep receipts 5 years.
- `## Tips for Foreigners` — combine the household's expenses under one filer; insurance reimbursements reduce the deductible amount.

- [ ] **Step 4: Create `knowledge/tax/12-tax-treaty-foreign-income.md`**

Front-matter: `doc_title: Tax Treaties and Foreign Income`, `source_url: https://www.nta.go.jp/english/taxes/individual/incometax_kojin.htm`, `language: en`, `last_updated: 2025-06-01`.
Sections & key content:
- `# Tax Treaties & Foreign Income (租税条約・国外所得)`.
- `## Residency for tax (居住者/非永住者/非居住者)` — resident, non-permanent resident (< 5 of last 10 yrs in Japan), non-resident — and what income each is taxed on.
- `## Non-permanent residents` — taxed on Japan-source income + foreign income paid in / remitted to Japan.
- `## Foreign tax credit (外国税額控除)` — relief from double taxation.
- `## Tax treaties (租税条約)` — reduced withholding; need a treaty notification form (租税条約に関する届出書); examples (students, researchers, dividends).
- `## Overseas assets reporting (国外財産調書)` — residents with > ¥50M foreign assets must report.
- `## Tips for Foreigners` — track years of residence; keep proof of foreign tax paid.

- [ ] **Step 5: Create `knowledge/tax/13-leaving-japan-tax.md`**

Front-matter: `doc_title: Tax When Leaving Japan`, `source_url: https://www.nta.go.jp/english/taxes/individual/incometax_kojin.htm`, `language: en`, `last_updated: 2025-06-01`.
Sections & key content:
- `# Tax When Leaving Japan (出国時の税金)`.
- `## File before you leave, or appoint a tax representative (納税管理人)` — if leaving mid-year with filing duty, either file before departure or appoint a 納税管理人 (tax agent) who files the following spring.
- `## Resident tax (住民税) lag` — resident tax is billed the year *after* the income year, based on Jan 1 residence; you may owe it after leaving — the tax agent or a lump-sum payment handles it.
- `## Pension lump-sum withdrawal (脱退一時金)` — short-stay leavers can claim a pension lump-sum after leaving; 20.42% tax may be reclaimed via the 納税管理人.
- `## Final steps` — moving-out notification (転出届), close NHI, settle resident tax.
- `## Tips for Foreigners` — appoint the tax agent **before** leaving; the resident-tax timing surprises many.

- [ ] **Step 6: Verify the 5 docs parse and hit the word target**

Run:
```bash
cd /Users/javagod/VsCodeProjects/JapanLife && for f in knowledge/tax/09-*.md knowledge/tax/1[0-3]-*.md; do printf "%-50s %4s words  " "$f" "$(wc -w < "$f"|tr -d ' ')"; head -1 "$f" | grep -q '^---$' && echo "front-matter OK" || echo "NO front-matter"; done
```
Expected: 5 lines, each ~300–500 words, each `front-matter OK`.

- [ ] **Step 7: Commit**

```bash
git add knowledge/tax/09-*.md knowledge/tax/1[0-3]-*.md
git commit -m "data(knowledge): add 5 English tax topic docs (consumption, dependents, medical, treaties, leaving Japan)"
```

## Task 3: Breadth — 5 new English visa docs (10–14)

**Files:** Create `knowledge/visa/10-highly-skilled-professional.md`, `11-naturalization-vs-pr.md`, `12-spouse-of-japanese.md`, `13-re-entry-permit.md`, `14-status-change-notifications.md`.

- [ ] **Step 1: Create `knowledge/visa/10-highly-skilled-professional.md`**

Front-matter: `doc_title: Highly-Skilled Professional Visa`, `source_url: https://www.moj.go.jp/isa/applications/status/index.html`, `language: en`, `last_updated: 2025-06-01`.
Sections & key content:
- `# Highly-Skilled Professional (高度専門職)`.
- `## Points system` — academic background, career, income, age scored; **70 points** qualifies (高度専門職1号).
- `## Benefits` — 5-year stay, faster PR (after **3 years**, or **1 year** at 80+ points), spouse can work, may bring parents/domestic helper under conditions, multiple activities allowed.
- `## 1号 vs 2号` — after 3 years on 1号 you can move to 高度専門職2号 (near-unlimited activities, indefinite stay).
- `## How to apply` — Certificate of Eligibility / change of status with the points calculation sheet.
- `## Tips for Foreigners` — recalc points yearly; income and a master's/PhD weigh heavily.

- [ ] **Step 2: Create `knowledge/visa/11-naturalization-vs-pr.md`**

Front-matter: `doc_title: Naturalization vs Permanent Residency`, `source_url: https://www.moj.go.jp/MINJI/minji78.html`, `language: en`, `last_updated: 2025-06-01`.
Sections & key content:
- `# Naturalization (帰化) vs Permanent Residency (永住)`.
- `## Permanent Residency` — keep your nationality, keep a residence card, lose status if you stay abroad too long without a re-entry permit; ~10 years residency typical.
- `## Naturalization` — become a Japanese citizen; Japan generally requires renouncing prior citizenship; ~5 years residency, basic Japanese ability, stable livelihood; handled by the **Legal Affairs Bureau (法務局)**, not immigration.
- `## Comparison table` — authority, nationality, passport, voting, re-entry, revocability.
- `## Which to choose` — PR for keeping nationality + flexibility; naturalization for full citizenship/voting.
- `## Tips for Foreigners` — naturalization paperwork is heavier; PR holders still need re-entry permits.

- [ ] **Step 3: Create `knowledge/visa/12-spouse-of-japanese.md`**

Front-matter: `doc_title: Spouse or Child of Japanese National Visa`, `source_url: https://www.moj.go.jp/isa/applications/status/index.html`, `language: en`, `last_updated: 2025-06-01`.
Sections & key content:
- `# Spouse/Child of Japanese National (日本人の配偶者等)`.
- `## Who is eligible` — spouses, biological/special-adopted children of Japanese nationals.
- `## Work freedom` — **no work restrictions** (unlike the Dependent visa), any job allowed.
- `## Periods` — 6 months / 1 / 3 / 5 years; renewable.
- `## Documents` — marriage registration (戸籍), proof of genuine marriage, income/tax docs.
- `## After divorce/bereavement` — must notify immigration within 14 days; risk of status loss if not remarried/changed; "Long-Term Resident (定住者)" may be possible.
- `## Path to PR` — spouses often qualify for PR after ~3 years marriage + 1 year residence.
- `## Tips for Foreigners` — report marital-status changes promptly.

- [ ] **Step 4: Create `knowledge/visa/13-re-entry-permit.md`**

Front-matter: `doc_title: Re-entry Permit Guide`, `source_url: https://www.moj.go.jp/isa/publications/materials/nyuukokukanri07_00078.html`, `language: en`, `last_updated: 2025-06-01`.
Sections & key content:
- `# Re-entry Permit (再入国許可)`.
- `## Special Re-entry Permit (みなし再入国)` — if you return within **1 year** (PR: within the residence-card validity), just tick the box on the embarkation card (ED card) — no fee. Cannot extend from abroad.
- `## Regular Re-entry Permit` — needed if away **longer than 1 year** (up to 5 years; PR up to 6); apply at immigration; fees apply (single/multiple).
- `## Why it matters` — leaving without it can void your residence status / PR.
- `## Tips for Foreigners` — for trips > 1 year, get the regular permit **before** leaving; mark special re-entry on departure.

- [ ] **Step 5: Create `knowledge/visa/14-status-change-notifications.md`**

Front-matter: `doc_title: Notifications for Changes in Status`, `source_url: https://www.moj.go.jp/isa/applications/procedures/16-8.html`, `language: en`, `last_updated: 2025-06-01`.
Sections & key content:
- `# Reporting Changes to Immigration (届出義務)`.
- `## Notify within 14 days` — changes of employer/affiliated organization, divorce/death of spouse (for status based on it), name/nationality changes.
- `## Address changes` — register at the ward office (転入/転居届) within 14 days — this feeds immigration.
- `## How to notify` — in person, by mail, or via the **e-Notification (電子届出)** system; bring residence card.
- `## Consequences of not reporting` — fines, harm to future renewals/PR.
- `## Tips for Foreigners` — keep copies; the employer-change notice is easy to forget.

- [ ] **Step 6: Verify**

Run:
```bash
cd /Users/javagod/VsCodeProjects/JapanLife && for f in knowledge/visa/1[0-4]-*.md; do printf "%-52s %4s words  " "$f" "$(wc -w < "$f"|tr -d ' ')"; head -1 "$f" | grep -q '^---$' && echo "fm OK" || echo "NO fm"; done
```
Expected: 5 lines, ~300–500 words each, `fm OK`.

- [ ] **Step 7: Commit**

```bash
git add knowledge/visa/1[0-4]-*.md
git commit -m "data(knowledge): add 5 English visa topic docs (HSP, naturalization, spouse, re-entry, notifications)"
```

---

## Task 4: Breadth — 5 new English ward_office docs (10–14)

**Files:** Create `knowledge/ward_office/10-child-allowance.md`, `11-health-checkups-vaccinations.md`, `12-certificates.md`, `13-drivers-license-conversion.md`, `14-disaster-emergency.md`.

- [ ] **Step 1: Create `knowledge/ward_office/10-child-allowance.md`**

Front-matter: `doc_title: Child Allowance and Childbirth Support`, `source_url: https://www.cfa.go.jp/policies/kokoseido/jidouteate/`, `language: en`, `last_updated: 2025-06-01`.
Sections & key content:
- `# Child Allowance & Childbirth (児童手当・出産)`.
- `## Child Allowance (児童手当)` — monthly payment for children (paid to residents regardless of nationality); apply at the ward office after birth/moving in; paid in installments.
- `## Childbirth lump-sum (出産育児一時金)` — ~¥500,000 per child via health insurance.
- `## Notification of birth (出生届)` — submit within **14 days** at the ward office; needed for registration, insurance, My Number.
- `## Maternal & Child Health Handbook (母子健康手帳)` — get it at the ward office when pregnant; used for checkups/vaccinations.
- `## Tips for Foreigners` — apply for child allowance the same day you register the birth; allowances are not retroactive far back.

- [ ] **Step 2: Create `knowledge/ward_office/11-health-checkups-vaccinations.md`**

Front-matter: `doc_title: Health Checkups and Vaccinations`, `source_url: https://www.mhlw.go.jp/english/`, `language: en`, `last_updated: 2025-06-01`.
Sections & key content:
- `# Health Checkups & Vaccinations (健診・予防接種)`.
- `## Infant/child checkups (乳幼児健診)` — free checkups at set ages, notified by the ward.
- `## Child vaccinations (定期予防接種)` — routine immunizations subsidized; schedule in the 母子手帳.
- `## Adult/specific health checkup (特定健診)` — for NHI members 40–74; metabolic-syndrome screening.
- `## Cancer screenings (がん検診)` — subsidized municipal screenings.
- `## How to use` — vouchers/notices mailed to your registered address.
- `## Tips for Foreigners` — update your address so notices arrive; many checkups are free or low-cost.

- [ ] **Step 3: Create `knowledge/ward_office/12-certificates.md`**

Front-matter: `doc_title: Common Certificates from the Ward Office`, `source_url: https://www.soumu.go.jp/main_sosiki/jichi_gyousei/c-gyousei/`, `language: en`, `last_updated: 2025-06-01`.
Sections & key content:
- `# Common Certificates (各種証明書)`.
- `## Residence certificate (住民票)` — proof of address; for contracts, banking.
- `## Seal registration certificate (印鑑登録証明書)` — proof your registered seal (実印) is yours; for car/property.
- `## Tax certificates (課税証明書/納税証明書)` — income/tax-paid proof; for visa renewal, loans.
- `## Where & how` — ward office counter, mail, or **convenience-store issuance** with a My Number card; small fee each (~¥300).
- `## Tips for Foreigners` — visa renewals often need 住民票 + tax certificates; My Number card lets you print at conbini.

- [ ] **Step 4: Create `knowledge/ward_office/13-drivers-license-conversion.md`**

Front-matter: `doc_title: Converting a Foreign Driver's License`, `source_url: https://www.npa.go.jp/policies/application/license_renewal/index.html`, `language: en`, `last_updated: 2025-06-01`.
Sections & key content:
- `# Converting a Foreign License (外免切替)`.
- `## What it is` — exchange an overseas license for a Japanese one via the licensing center (運転免許試験場).
- `## Requirements` — valid foreign license, proof of **3+ months** driving in the issuing country, official Japanese translation (e.g., JAF), passport, residence card, 住民票.
- `## Process` — document check → knowledge/aptitude test → practical test (waived for some countries).
- `## International Driving Permit (国際運転免許)` — valid up to 1 year for short stays; residents should convert.
- `## Tips for Foreigners` — book early (slots fill); get the JAF translation in advance.

- [ ] **Step 5: Create `knowledge/ward_office/14-disaster-emergency.md`**

Front-matter: `doc_title: Disaster Preparedness and Emergencies`, `source_url: https://www.bousai.go.jp/`, `language: en`, `last_updated: 2025-06-01`.
Sections & key content:
- `# Disaster Preparedness & Emergencies (防災・緊急時)`.
- `## Emergency numbers` — **110** police, **119** fire/ambulance; explain how to state your address.
- `## Earthquakes/typhoons` — basics; evacuation areas (避難所) registered by the ward; hazard maps.
- `## Emergency alerts` — J-Alert / area-mail to phones; disaster apps with multilingual support (NHK World, Safety tips).
- `## Evacuation prep` — go-bag, family meeting point, water/food stock.
- `## Foreign-resident support` — multilingual disaster info lines; the ward distributes hazard maps.
- `## Tips for Foreigners` — check your nearest 避難所 now; keep your residence card + a little cash in your go-bag.

- [ ] **Step 6: Verify**

Run:
```bash
cd /Users/javagod/VsCodeProjects/JapanLife && for f in knowledge/ward_office/1[0-4]-*.md; do printf "%-58s %4s words  " "$f" "$(wc -w < "$f"|tr -d ' ')"; head -1 "$f" | grep -q '^---$' && echo "fm OK" || echo "NO fm"; done
```
Expected: 5 lines, ~300–500 words each, `fm OK`.

- [ ] **Step 7: Commit**

```bash
git add knowledge/ward_office/1[0-4]-*.md
git commit -m "data(knowledge): add 5 English ward-office topic docs (child allowance, health, certificates, license, disaster)"
```

## Task 5: Depth — expand the thinnest docs

**Files:** Modify `knowledge/visa/01-visa-types.md`, `knowledge/visa/02-renewal.md`, `knowledge/ward_office/01-moving-in.md`, `knowledge/ward_office/02-my-number.md`. Keep each file's front-matter and `doc_id` (filename) unchanged — only grow the body to ~350–450 words.

- [ ] **Step 1: Expand `knowledge/visa/01-visa-types.md`**

Keep the existing front-matter and the three current sections (Work / PR / Dependent). Add sections so the doc covers the common statuses:
- `## Engineer/Specialist in Humanities/International Services (技術・人文知識・国際業務)` — expand the work-visa detail (degree match, employer tie).
- `## Highly-Skilled Professional (高度専門職)` — one-paragraph pointer (points-based, PR fast-track) — cross-reference topic.
- `## Student (留学) and Designated Activities (特定活動)` — study status, 28h/week with permit.
- `## Specified Skilled Worker (特定技能)` — labor-shortage sectors, 1号/2号.
- `## Business Manager (経営・管理)` — running a company.
- Keep a closing `## Choosing the right status` note. Target ~400 words.

- [ ] **Step 2: Expand `knowledge/visa/02-renewal.md`**

Keep front-matter. Build it out to ~400 words with:
- `## When to apply` — from **3 months before** expiry; don't overstay.
- `## Required documents` — application form, passport, residence card, photo, employment/income proof (在職証明・課税/納税証明書), company docs.
- `## Processing time` — typically **2 weeks–1 month**; "under examination" lets you stay past expiry up to 2 months.
- `## Period granted` — 1/3/5 years depends on history, income, tax/pension compliance.
- `## Common reasons for trouble` — unpaid tax/pension, job mismatch, overstays.
- `## Tips for Foreigners` — pay pension/tax (checked at renewal); apply early.

- [ ] **Step 3: Expand `knowledge/ward_office/01-moving-in.md`**

Keep front-matter and the existing 转入届/住民票 sections. Add to reach ~400 words:
- `## Within 14 days` — emphasize the deadline and same-trip errands.
- `## What to bring` — residence card(s) for all members, 転出証明書 (if from another Japanese city), passports, My Number notification.
- `## Procedures bundled at move-in` — National Health Insurance (国保) enrollment, National Pension (国民年金), child allowance (児童手当), My Number address update, seal registration (印鑑登録) if needed.
- `## Moving within the same city (転居届)` — different form, still 14 days.
- `## Tips for Foreigners` — do bank/phone/utility setup after you get the 住民票; bring everyone's residence cards.

- [ ] **Step 4: Expand `knowledge/ward_office/02-my-number.md`**

Keep front-matter. Build to ~400 words:
- `## What is My Number (マイナンバー)` — 12-digit ID for tax, social security, disaster response.
- `## Notification vs Card` — paper notification vs the **My Number Card (マイナンバーカード)** with IC chip + photo.
- `## What the card does` — official photo ID, conbini issuance of 住民票/印鑑証明, e-Tax login, linked health-insurance card (マイナ保険証).
- `## How to get the card` — apply online/mail/at ward; pick up in person.
- `## When you need My Number` — employer, bank, tax filing.
- `## Tips for Foreigners` — keep the number private; the card greatly simplifies paperwork; update the card's address when you move.

- [ ] **Step 5: Verify the four docs grew to target**

Run:
```bash
cd /Users/javagod/VsCodeProjects/JapanLife && for f in knowledge/visa/01-visa-types.md knowledge/visa/02-renewal.md knowledge/ward_office/01-moving-in.md knowledge/ward_office/02-my-number.md; do printf "%-50s %4s words\n" "$f" "$(wc -w < "$f"|tr -d ' ')"; done
```
Expected: each now ~330–470 words (up from 122–146).

- [ ] **Step 6: Commit**

```bash
git add knowledge/visa/01-visa-types.md knowledge/visa/02-renewal.md knowledge/ward_office/01-moving-in.md knowledge/ward_office/02-my-number.md
git commit -m "data(knowledge): deepen thin visa/ward-office docs to full depth"
```

---

## Task 6: Native Japanese — 9 parallel `.ja.md` docs

**Files:** Create 9 files with `language: ja` front-matter and natural Japanese bodies (not literal translations). Same topic/structure as the English counterpart. `doc_title` in Japanese; reuse the counterpart's `source_url`; `last_updated: 2025-06-01`.

- [ ] **Step 1: Create the 3 tax JA docs**

`knowledge/tax/01-tax-filing-overview.ja.md` — `doc_title: 確定申告の基礎ガイド`. Sections: `# 確定申告の基礎`, `## 申告期間`（2/16–3/15）, `## 申告が必要な人`（給与2,000万円超・副業所得20万円超など）, `## e-Tax`, `## 外国人向けの注意`.

`knowledge/tax/04-furusato-nozei.ja.md` — `doc_title: ふるさと納税ガイド`. Sections: `# ふるさと納税とは`, `## 仕組み（自己負担2,000円・返礼品）`, `## 控除限度額の目安`（収入別の表、~¥ 約数）, `## ワンストップ特例 と 確定申告`, `## 外国人向けの注意`.

`knowledge/tax/08-resident-tax.ja.md` — `doc_title: 住民税ガイド`. Sections: `# 住民税`, `## 仕組み（前年所得・1月1日居住地）`, `## 税率の目安（約10%）`, `## 納付方法（特別徴収/普通徴収）`, `## 退職・出国時の注意`.

- [ ] **Step 2: Create the 3 visa JA docs**

`knowledge/visa/01-visa-types.ja.md` — `doc_title: 在留資格の種類`. Sections: `# 主な在留資格`, `## 就労ビザ（技術・人文知識・国際業務）`, `## 永住`, `## 家族滞在`, `## 留学・特定技能` の概要.

`knowledge/visa/04-permanent-residency.ja.md` — `doc_title: 永住許可ガイド`. Sections: `# 永住許可`, `## 要件（原則10年・うち就労5年）`, `## 高度人材の特例（1〜3年）`, `## 必要書類（納税・年金記録、身元保証人）`, `## 注意点`.

`knowledge/visa/02-renewal.ja.md` — `doc_title: 在留期間の更新`. Sections: `# 在留期間更新`, `## 申請時期（満了の3か月前から）`, `## 必要書類`, `## 審査期間`, `## 不許可になりやすい理由（税・年金未納）`.

- [ ] **Step 3: Create the 3 ward_office JA docs**

`knowledge/ward_office/01-moving-in.ja.md` — `doc_title: 転入届ガイド`. Sections: `# 転入届`, `## 14日以内の届出`, `## 持ち物（在留カード・転出証明書）`, `## 同時に行う手続き（国保・年金・児童手当）`, `## 注意`.

`knowledge/ward_office/05-national-health-insurance.ja.md` — `doc_title: 国民健康保険ガイド`. Sections: `# 国民健康保険（国保）`, `## 加入対象（職場の保険に入らない人）`, `## 保険料（前年所得ベース）`, `## 給付（自己負担3割）`, `## 手続き`.

`knowledge/ward_office/06-national-pension.ja.md` — `doc_title: 国民年金ガイド`. Sections: `# 国民年金`, `## 加入対象（20〜60歳）`, `## 保険料・免除制度`, `## 出国時の脱退一時金`, `## 手続き`.

- [ ] **Step 4: Verify the 9 JA docs parse, are Japanese, and tagged `language: ja`**

Run:
```bash
cd /Users/javagod/VsCodeProjects/JapanLife && for f in knowledge/*/*.ja.md; do L=$(grep -m1 '^language:' "$f"); JA=$(grep -cE '[぀-ヿ㐀-鿿]' "$f"); printf "%-50s %s  jp-lines:%s\n" "$f" "$L" "$JA"; done
```
Expected: 9 files, each `language: ja`, each with many `jp-lines` (Japanese present).

- [ ] **Step 5: Confirm ingest still globs everything (count docs)**

Run:
```bash
cd /Users/javagod/VsCodeProjects/JapanLife && python3 -c "from rag.ingest import load_documents; d=load_documents(); print('docs:', len(d)); import collections; print(collections.Counter(x[0] for x in d))"
```
Expected: `docs: 50` (or ~50), with each domain's count including the new `.ja.md` files.

- [ ] **Step 6: Commit**

```bash
git add knowledge/*/*.ja.md
git commit -m "data(knowledge): add 9 native-Japanese parallel docs (tax/visa/ward_office)"
```

## Task 7: Eval — expand retrieval + answer datasets

**Files:** Append to `eval/datasets/tax.jsonl`, `eval/datasets/visa.jsonl`, `eval/datasets/ward_office.jsonl`, `eval/datasets/answer_cases.jsonl`. **Do Tasks 2–6 first** — the integrity test requires every `relevant` doc_id to exist on disk.

- [ ] **Step 1: Append tax retrieval cases**

Append these lines verbatim to `eval/datasets/tax.jsonl`:
```jsonl
{"question": "What is the consumption tax rate in Japan?", "relevant": ["tax/09-consumption-tax.md"], "lang": "en", "type": "keyword"}
{"question": "テイクアウトと店内飲食で消費税率は違いますか", "relevant": ["tax/09-consumption-tax.md"], "lang": "ja", "type": "numeric"}
{"question": "How much is the dependent deduction worth?", "relevant": ["tax/10-dependents-deductions.md"], "lang": "en", "type": "numeric"}
{"question": "扶養に入れる年収の上限はいくらですか", "relevant": ["tax/10-dependents-deductions.md"], "lang": "ja", "type": "numeric"}
{"question": "Can I deduct my medical expenses on my tax return?", "relevant": ["tax/11-medical-expense-deduction.md"], "lang": "en", "type": "semantic"}
{"question": "医療費控除は年末調整でできますか", "relevant": ["tax/11-medical-expense-deduction.md", "tax/05-year-end-adjustment.md"], "lang": "ja", "type": "confusing"}
{"question": "I am a non-permanent resident, is my foreign income taxed?", "relevant": ["tax/12-tax-treaty-foreign-income.md"], "lang": "en", "type": "semantic"}
{"question": "What happens to my resident tax if I leave Japan mid-year?", "relevant": ["tax/13-leaving-japan-tax.md", "tax/08-resident-tax.md"], "lang": "en", "type": "cross"}
{"question": "確定申告の期間を教えてください", "relevant": ["tax/01-tax-filing-overview.ja.md", "tax/01-tax-filing-overview.md"], "lang": "ja", "type": "semantic"}
{"question": "ふるさと納税の自己負担はいくらですか", "relevant": ["tax/04-furusato-nozei.ja.md", "tax/04-furusato-nozei.md"], "lang": "ja", "type": "numeric"}
{"question": "住民税はいつの所得を基準に計算されますか", "relevant": ["tax/08-resident-tax.ja.md", "tax/08-resident-tax.md"], "lang": "ja", "type": "semantic"}
```

- [ ] **Step 2: Append visa retrieval cases**

Append to `eval/datasets/visa.jsonl`:
```jsonl
{"question": "How many points do I need for the Highly-Skilled Professional visa?", "relevant": ["visa/10-highly-skilled-professional.md"], "lang": "en", "type": "numeric"}
{"question": "高度専門職だと永住は何年で申請できますか", "relevant": ["visa/10-highly-skilled-professional.md", "visa/04-permanent-residency.md"], "lang": "ja", "type": "cross"}
{"question": "What is the difference between naturalization and permanent residency?", "relevant": ["visa/11-naturalization-vs-pr.md"], "lang": "en", "type": "semantic"}
{"question": "Can a spouse of a Japanese national work without restrictions?", "relevant": ["visa/12-spouse-of-japanese.md"], "lang": "en", "type": "semantic"}
{"question": "再入国許可は何年以内の帰国なら不要ですか", "relevant": ["visa/13-re-entry-permit.md"], "lang": "ja", "type": "numeric"}
{"question": "Do I need to tell immigration if I change jobs?", "relevant": ["visa/14-status-change-notifications.md"], "lang": "en", "type": "keyword"}
{"question": "在留資格の種類にはどんなものがありますか", "relevant": ["visa/01-visa-types.ja.md", "visa/01-visa-types.md"], "lang": "ja", "type": "semantic"}
{"question": "永住許可の要件は何年の在留ですか", "relevant": ["visa/04-permanent-residency.ja.md", "visa/04-permanent-residency.md"], "lang": "ja", "type": "numeric"}
{"question": "在留期間の更新はいつから申請できますか", "relevant": ["visa/02-renewal.ja.md", "visa/02-renewal.md"], "lang": "ja", "type": "numeric"}
```

- [ ] **Step 3: Append ward_office retrieval cases**

Append to `eval/datasets/ward_office.jsonl`:
```jsonl
{"question": "How do I apply for the child allowance?", "relevant": ["ward_office/10-child-allowance.md"], "lang": "en", "type": "semantic"}
{"question": "出生届は何日以内に出す必要がありますか", "relevant": ["ward_office/10-child-allowance.md"], "lang": "ja", "type": "numeric"}
{"question": "Are child vaccinations free in Japan?", "relevant": ["ward_office/11-health-checkups-vaccinations.md"], "lang": "en", "type": "semantic"}
{"question": "How can I get a residence certificate at a convenience store?", "relevant": ["ward_office/12-certificates.md", "ward_office/04-residence-record.md"], "lang": "en", "type": "confusing"}
{"question": "外国の運転免許を日本の免許に切り替えるには何が必要ですか", "relevant": ["ward_office/13-drivers-license-conversion.md"], "lang": "ja", "type": "semantic"}
{"question": "What number do I call for an ambulance in Japan?", "relevant": ["ward_office/14-disaster-emergency.md"], "lang": "en", "type": "numeric"}
{"question": "転入届は何日以内に提出しますか", "relevant": ["ward_office/01-moving-in.ja.md", "ward_office/01-moving-in.md"], "lang": "ja", "type": "numeric"}
{"question": "国民健康保険には誰が加入しますか", "relevant": ["ward_office/05-national-health-insurance.ja.md", "ward_office/05-national-health-insurance.md"], "lang": "ja", "type": "semantic"}
{"question": "国民年金は何歳から加入しますか", "relevant": ["ward_office/06-national-pension.ja.md", "ward_office/06-national-pension.md"], "lang": "ja", "type": "numeric"}
```

- [ ] **Step 4: Append answer-eval cases**

Append to `eval/datasets/answer_cases.jsonl`:
```jsonl
{"question": "What is the consumption tax rate on groceries?", "expected_route": "tax", "expects_disclaimer": true, "lang": "en"}
{"question": "医療費控除はいくらから受けられますか", "expected_route": "tax", "expects_disclaimer": true, "lang": "ja"}
{"question": "How much is the dependent deduction?", "expected_route": "tax", "expects_disclaimer": true, "lang": "en"}
{"question": "高度専門職ビザのポイントは何点必要ですか", "expected_route": "visa", "expects_disclaimer": true, "lang": "ja"}
{"question": "Can the spouse of a Japanese citizen work freely?", "expected_route": "visa", "expects_disclaimer": true, "lang": "en"}
{"question": "再入国許可なしで何年まで日本を離れられますか", "expected_route": "visa", "expects_disclaimer": true, "lang": "ja"}
{"question": "How do I apply for the child allowance?", "expected_route": "ward_office", "expects_disclaimer": false, "lang": "en"}
{"question": "外国の運転免許を切り替えるには何が必要ですか", "expected_route": "ward_office", "expects_disclaimer": false, "lang": "ja"}
{"question": "What should I prepare for an earthquake?", "expected_route": "ward_office", "expects_disclaimer": false, "lang": "en"}
{"question": "I am leaving Japan, what should I do about resident tax?", "expected_route": ["tax", "ward_office"], "expects_disclaimer": true, "lang": "en"}
```

- [ ] **Step 5: Run the dataset-integrity suite**

Run:
```bash
cd /Users/javagod/VsCodeProjects/JapanLife && poetry run pytest tests/test_eval_datasets.py tests/test_answer_eval.py -v
```
Expected: all PASS. Specifically `test_relevant_doc_ids_exist_on_disk` passes (every `relevant` doc exists), `test_each_domain_has_at_least_20_cases` passes, `test_language_tags_are_valid` passes, `test_datasets_cover_required_query_types` passes.

If `test_relevant_doc_ids_exist_on_disk` fails, a doc filename doesn't match its eval `relevant` id — fix the filename or the id so they match exactly.

- [ ] **Step 6: Verify counts**

Run:
```bash
cd /Users/javagod/VsCodeProjects/JapanLife && for d in tax visa ward_office; do echo "$d: $(grep -c . eval/datasets/$d.jsonl) cases"; done; echo "answer: $(grep -c . eval/datasets/answer_cases.jsonl) cases"
```
Expected: tax ~33, visa ~31, ward_office ~31 (total ~95–100); answer ~25.

- [ ] **Step 7: Commit**

```bash
git add eval/datasets/tax.jsonl eval/datasets/visa.jsonl eval/datasets/ward_office.jsonl eval/datasets/answer_cases.jsonl
git commit -m "eval: expand retrieval + answer datasets to cover new docs (incl. JA cases)"
```

---

## Task 8: Wrap-up — counts, README, full suite

**Files:** Modify `README.md`.

- [ ] **Step 1: Verify final corpus size hits the target**

Run:
```bash
cd /Users/javagod/VsCodeProjects/JapanLife && echo "docs: $(find knowledge -name '*.md' | wc -l | tr -d ' ')"; echo "words: $(cat knowledge/*/*.md | wc -w | tr -d ' ')"; for d in knowledge/*/; do echo "$d $(find "$d" -name '*.md' | wc -l | tr -d ' ') docs"; done
```
Expected: ~50 docs, ~16k–19k words, each domain grown.

- [ ] **Step 2: Update README eval/doc-count references**

In `README.md`, update the two "66 cases" mentions to the new total. Change line ~42:
```
- **Two-axis evaluation** — retrieval eval (Recall@5 / MRR over ~95 cases) **and** answer eval
```
And line ~194:
```
- **Retrieval eval** (`make eval`) — Recall@5 / MRR over **~95 cases** (≥30 per domain, EN/JA/
```
(Use the actual total from Task 7 Step 6.) Also adjust the Highlights/intro wording if it states a specific small knowledge-base size.

- [ ] **Step 3: Run the full unit suite (no services needed)**

Run:
```bash
cd /Users/javagod/VsCodeProjects/JapanLife && make test
```
Expected: all unit tests pass (the previous 121 plus the dataset tests still green). No integration/services required.

- [ ] **Step 4: (Optional, if ES+Qdrant available) re-ingest and sanity-check retrieval**

Run:
```bash
cd /Users/javagod/VsCodeProjects/JapanLife && make up && make ingest && make eval
```
Expected: ingest reports ~50 documents; `make eval` prints Recall@5 / MRR over the expanded set. Skip if services/API key are unavailable — the suite in Step 3 already validates structure.

- [ ] **Step 5: Commit**

```bash
git add README.md
git commit -m "docs(readme): update eval case count and knowledge-base size after enrichment"
```

---

## Self-Review (completed)

**Spec coverage** — every spec section maps to a task:
- §3 Breadth (15 EN docs) → Tasks 2, 3, 4.
- §4 Native Japanese (9 `.ja.md`) → Task 6.
- §5 Depth (thin docs) → Task 5.
- §6 Hygiene (`language: en` ×7) → Task 1.
- §7 Eval expansion + integrity + field/order constraints → Task 7 (docs created first in Tasks 2–6).
- §8 Accuracy/sourcing → encoded as `source_url` + approximate-figure style in every doc step.
- §10 milestones → Tasks 1–8 in order; word/count target verified in Task 8.

**Placeholder scan** — no "TBD/implement later". Each new doc has a concrete filename, front-matter values, section headers, and the specific facts to include (the content analog of a signature + behavior). Eval cases are shown as exact JSONL deliverables.

**Consistency** — `doc_id`s used in Task 7 `relevant` arrays exactly match filenames created in Tasks 2–6 (e.g. `tax/09-consumption-tax.md`, `tax/01-tax-filing-overview.ja.md`). Retrieval `type` values stay within {keyword, semantic, numeric, cross, confusing}; `lang` within {en, ja, mixed}. Order constraint (docs before eval) is stated in Task 7's intro. Each domain ends ≥20 cases (22 existing + new).

---

## Execution Handoff

Plan complete and saved to `docs/superpowers/plans/2026-06-19-japanlife-knowledge-base-enrichment.md`.



