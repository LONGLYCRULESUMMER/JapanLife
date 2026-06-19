# JapanLife 知识库扩充设计文档 — 三领域 RAG 数据加深

- **日期**: 2026-06-19
- **状态**: 待用户评审
- **作者**: @coda1997 + Copilot
- **定位**: 简历级 Agent 项目的「知识库做深 + 真·双语内容」（增强混合检索 RAG 的数据基础）

---

## 1. 背景与目标

现有 `JapanLife` 后端具备完整的混合检索 RAG（ES BM25 + kuromoji ∥ Qdrant BGE-m3 → RRF → 重排）与三领域多智能体（tax / visa / ward_office）。但**知识库内容偏薄**：

- 共 **26 篇文档 / ~7,500 词**（tax=8、visa=9、ward_office=9）。
- 多篇过短：`visa/01-visa-types`(146w)、`visa/02-renewal`(140w)、`ward_office/01-moving-in`(124w)、`ward_office/02-my-number`(122w)。
- **没有任何原生日语文档**：全部 `language: en`；但评测集里有日语 query（如「確定申告の期間…」）在检索英文文档——「双语」目前只是跨语种检索，而非双语内容。
- 7 篇 tax 文档缺 `language:` front-matter 字段。
- 评测：检索 66 例（en+ja）+ 回答 15 例，`relevant` 指向 `tax/01-…md` 形式的 doc_id。

**目标**：把语料从 **26 篇 / ~7.5k 词** 扩到 **~50 篇 / ~18k 词**，三领域同时做**广度 + 深度 + 原生日语**，并扩充评测集覆盖新内容，让「混合检索 / 双语 / 已评测」三个卖点都有实打实的数据支撑。

### 成功标准

1. 文档数 ~50、总词数 ~18k，三领域均衡增长。
2. 新增 **15 篇英文新主题** + **9 篇原生日语平行文档**（`language: ja`）。
3. 扩充后的检索/回答评测集全部通过数据完整性校验（每个 `relevant` doc_id 都能解析到真实文件）。
4. 现有 121 单测保持绿色；ingest 为纯数据变更，不改代码。

### 非目标（Out of Scope）

- 不改 chunking / ingest / 检索 / agent 代码逻辑（除非数据暴露出 bug）。
- 不追求逐字翻译：日语文档是同主题的**自然日语原生内容**，非 EN 的 1:1 译文。
- 不做权威法律级事实核验：内容为通用信息性指引（App 已有「非法律/税务意见」免责声明），关键数字保留官方 `source_url` 并按现有 `~¥` 风格给约数。

---

## 2. 现状与数据管线（复用，不改）

- **文档格式**：Markdown + 可选 front-matter（`doc_title` / `source_url` / `language` / `last_updated`）。
- **加载**：`rag/ingest.py` 以 `knowledge/*/*.md` glob 读取；`domain=父目录名`，`doc_id=domain/filename`。
- **切块**：`rag/chunking.py` 按 Markdown 标题分节，再按 1200 字符 / 150 重叠二次切块；`language` 缺省回退 `"mixed"`。
- **关键点**：`.ja.md` 文件天然匹配 `*/*.md` glob，`doc_id` 形如 `tax/01-tax-filing-overview.ja.md`，与英文版区分；chunker 与语言无关，可直接处理日语正文。

---

## 3. 广度 — 新增 15 篇英文主题文档

每篇 ~350–450 词，沿用现有结构（标题分节 + 表格/清单 +「Tips for Foreigners」），含官方 `source_url`。

| 领域 | 新文件（编号续接） |
| --- | --- |
| **tax** | `09-consumption-tax.md` 消費税 · `10-dependents-deductions.md` 扶養控除 · `11-medical-expense-deduction.md` 医療費控除 · `12-tax-treaty-foreign-income.md` 租税条約/海外所得 · `13-leaving-japan-tax.md` 离日：最终申报与納税管理人 |
| **visa** | `10-highly-skilled-professional.md` 高度専門職 · `11-naturalization-vs-pr.md` 帰化と永住 · `12-spouse-of-japanese.md` 日本人の配偶者等 · `13-re-entry-permit.md` 再入国許可 · `14-status-change-notifications.md` 在留変更时的届出 |
| **ward_office** | `10-child-allowance.md` 児童手当・出産 · `11-health-checkups-vaccinations.md` 健診・予防接種 · `12-certificates.md` 住民票・印鑑証明 · `13-drivers-license-conversion.md` 外免切替 · `14-disaster-emergency.md` 防災・緊急時 |

---

## 4. 原生日语 — 新增 9 篇平行文档（`language: ja`）

挑选三领域高频主题，写成**自然日语原生文档**（同结构、日语正文），文件名 `NN-name.ja.md`：

- `tax/01-tax-filing-overview.ja.md`、`tax/04-furusato-nozei.ja.md`、`tax/08-resident-tax.ja.md`
- `visa/01-visa-types.ja.md`、`visa/04-permanent-residency.ja.md`、`visa/02-renewal.ja.md`
- `ward_office/01-moving-in.ja.md`、`ward_office/05-national-health-insurance.ja.md`、`ward_office/06-national-pension.ja.md`

**效果**：日语 query 经 ES kuromoji（原生分词命中）+ Qdrant BGE-m3（多语向量）可直接召回日语 chunk，真正体现「双语混合检索」。每篇 front-matter 标 `language: ja` + 官方 `source_url`。

---

## 5. 深度 — 扩写过薄文档

在**不改 doc_id**的前提下，把最薄文档扩到 ~350–450 词（补充小节、示例、边界情况）：

- 重点：`visa/01-visa-types`、`visa/02-renewal`、`ward_office/01-moving-in`、`ward_office/02-my-number`。
- 轻量一致性补充：`visa/05–08`、`ward_office/05–07` 视情况补全到同等深度。

---

## 6. 卫生项 — front-matter 一致性

给缺字段的 7 篇 tax 文档补 `language: en`：
`tax/01,02,03,04,05,06,07`（与其余文档对齐，使 ingest 元数据中 `language` 准确而非回退 `mixed`）。

---

## 7. 评测扩充

> 现有评测：`eval/datasets/{tax,visa,ward_office}.jsonl`（检索，行式：`question`/`relevant`/`lang`/`type`），`eval/datasets/answer_cases.jsonl`（回答，`question`/`expected_route`/`expects_disclaimer`/`lang`）。

- **检索集**：每篇**新英文文档** ~+2 例（混合 `en`/`ja`、`keyword`/`numeric`）；每篇**日语平行文档** +1–2 例日语 query，`relevant` 指向对应 `.ja.md`。总量 66 → **~100**。
- **回答集**：覆盖新主题/路由 ~+10 例（带 `expected_route` + `expects_disclaimer`）。15 → **~25**。
- **完整性**：运行既有 dataset-integrity 测试（`tests/test_eval_datasets.py`），确保每个 `relevant` doc_id 解析到真实文件；新文档命名与 doc_id 严格一致。
- **字段约束**（须满足现有测试）：`lang ∈ {en, ja, mixed}`；`type` 取值须来自 `{keyword, semantic, numeric, cross, confusing}`（测试要求这五类至少各出现一次，扩充时沿用既有取值即可）；每域 `≥20` 例。
- **顺序约束**：因 `test_relevant_doc_ids_exist_on_disk` 要求 `relevant` 指向真实文件，**先落地文档、再加对应评测例**（实现计划据此排序）。

---

## 8. 数据准确性与来源

- 每篇保留 `doc_title` + 官方 `source_url`（nta.go.jp / moj.go.jp/isa / soumu.go.jp / 市区町村站点）+ `last_updated`。
- 内容为成熟的通用信息性指引；随情形变化的金额给**约数**（沿用现有 `~¥` 风格）。
- 对少量高风险具体数字（如消費税税率 10%/8%、児童手当 基本框架）做 **web 核验**后再落地。
- App 层已有「仅供参考，非法律/税务意见」免责声明，文档不替代官方咨询。

---

## 9. 风险与权衡

- **事实时效**：税制/在留规则会变；以官方 `source_url` + `last_updated` 标注，并保持约数，降低过期风险。
- **新增文档影响既有检索指标**：语料变大可能把既有 query 的相关文档轻微挤下排名；新主题与既有主题区分度高，风险低；以 `make eval` 复测把关。
- **日语内容质量**：原生撰写而非机翻，保证 kuromoji 分词与向量召回质量。
- **纯数据变更**：不动 ingest/检索代码，回归面小；如发现 chunking 对日语有问题再单独处理。

---

## 10. 交付里程碑（供实现计划参考）

1. 卫生项：7 篇 tax 文档补 `language: en`。
2. 广度：tax 5 篇英文新文档。
3. 广度：visa 5 篇英文新文档。
4. 广度：ward_office 5 篇英文新文档。
5. 深度：扩写 4 篇最薄文档（+ 视情况的一致性补充）。
6. 日语：tax/visa/ward 各 3 篇 `.ja.md` 平行文档。
7. 评测：扩充三领域检索集 + answer_cases，跑通 dataset-integrity 测试。
8. 收尾：词数/篇数核对（~50 篇 / ~18k 词），121 单测保持绿色，更新 README/知识库统计（如有）。

---

*本设计经三小节逐段评审通过后成稿，等待用户最终评审，随后进入实现计划（writing-plans）。*
