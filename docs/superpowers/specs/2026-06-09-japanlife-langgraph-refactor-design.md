# JapanLife 重构设计文档 — LangGraph 多智能体 + 混合检索 RAG

- **日期**: 2026-06-09
- **状态**: 已批准（待实现计划）
- **作者**: @coda1997 + Copilot
- **定位**: 简历级 Agent 项目（面向 GitHub 展示 / 面试讲解）

---

## 1. 背景与目标

现有 `JapanLife` 项目基于 **Google ADK + Claude**，是一个面向在日外国人的多智能体助手（7 个领域子 agent + ChromaDB RAG），但仅 tax 领域有数据，MCP / API 仅占位。

本次重构的目标：把它改造成一个**技术深度突出、可一键演示、可写进简历的现代 Agent 项目**，技术栈对齐当前业界主流：

- **LangChain + LangGraph** 构建有状态多智能体
- **混合检索（Hybrid Search）RAG**：ElasticSearch（BM25）+ Qdrant（向量）
- **FastAPI** 服务化
- **DeepSeek** 作为 LLM（性价比高、OpenAI 兼容）
- **docker-compose** 一键部署 + **RAG 评测** + 单测 + 完整 README

成功标准：

1. `docker-compose up` 一键拉起 ES + Qdrant + API，本地可对话演示。
2. 检索层能跑出**混合检索 vs 纯向量基线**的 recall@k / MRR 对比指标（简历硬数据）。
3. multi-agent 编排清晰，含一处真实的专家间 handoff，面试可讲。
4. 有单测 + RAG eval + 完整 README。

---

## 2. 范围

### In Scope（本期交付）
- 3 个做深的领域：**tax（税务）/ visa（在留）/ ward_office（区役所）**
- supervisor 路由 + 3 个专家子图 + 1 处 handoff（ward_office → visa/tax）
- 混合检索流水线（ES BM25 + Qdrant 向量 + RRF 融合 + cross-encoder 精排）
- FastAPI（`/chat`、`/chat/stream`、`/health`）
- SQLite checkpointer 持久化对话 + 多步流程状态
- docker-compose、RAG eval、pytest、README

### Out of Scope（本期不做，列入未来扩展）
- 其余 4 个领域（banking / employment / housing / health_pension）
- 独立前端 / Streamlit 页面（先用 API + `/docs` + CLI 演示）
- 生产级鉴权、多租户、限流、可观测平台
- 云端部署（仅本地 docker-compose）

---

## 3. 技术选型

| 层 | 选型 | 说明 |
|---|---|---|
| 编排 | **LangGraph** | supervisor + 3 专家子图 + 1 handoff |
| 组件 | **LangChain** | `@tool`、retriever 封装、ChatModel |
| LLM | **DeepSeek** | `langchain-deepseek` 的 `ChatDeepSeek`；默认 `deepseek-chat`（支持 tool calling） |
| 稀疏检索 | **ElasticSearch** | BM25 + `kuromoji` 日文分词 |
| 稠密检索 | **Qdrant** | 存 **BGE-m3** 多语言向量（1024 维） |
| 融合/精排 | **RRF** + **bge-reranker-v2-m3** | cross-encoder 重排 |
| 状态 | **SQLite checkpointer** | `langgraph-checkpoint-sqlite`，无需额外服务 |
| API | **FastAPI** | 含 SSE 流式 |
| 评测 | 自建 QA 集 | recall@k / MRR；可选 LLM-as-judge 忠实度 |
| 部署 | **docker-compose** | es + qdrant + api |
| 配置 | **pydantic-settings** | 环境变量集中管理 |

**关键解耦**：embedding（BGE-m3）与精排（bge-reranker）均**本地运行**，与 LLM 提供商完全解耦——更换 LLM（DeepSeek/OpenAI/Claude/本地）零成本，仅改 `core/llm.py` 一处工厂。

---

## 4. 架构总览

```
用户 ──HTTP──▶ FastAPI (/chat, /chat/stream, /health)
                     │  thread_id + message
                     ▼
            LangGraph 编排图  (SQLite checkpointer 持久化对话+流程状态)
                     │
            ┌────────┴────────┐
            ▼                 │
   Supervisor 节点            │ 检测语言(EN/JA) → 路由
   (router)                   │
            │ route           │ handoff (Command)
   ┌────────┼────────┐        │
   ▼        ▼        ▼        │
  tax     visa   ward_office ─┘  (ward_office ⇄ visa/tax 协作交接)
 子图     子图     子图
   │        │        │
   └────────┴────────┴──▶ 工具(@tool) + 混合检索
                                   │
              ┌────────────────────┴───────────────────┐
              ▼                                         ▼
   ElasticSearch (BM25 + kuromoji 日文分词)      Qdrant (BGE-m3 稠密向量)
              └──────────────► RRF 融合 ◄───────────────┘
                                   │
                        Cross-Encoder 重排 (bge-reranker-v2-m3)
                                   │
                          Top-N 结果 + citation 引用
```

---

## 5. 工程结构

每个模块单一职责、通过清晰接口通信、可独立测试。

```
japanlife/
├── app/                FastAPI 层
│   ├── main.py         应用入口、lifespan、依赖注入
│   ├── routes.py       /chat /chat/stream /health
│   └── schemas.py      请求/响应 Pydantic 模型
├── agents/             LangGraph 多智能体
│   ├── graph.py        组装 supervisor + 专家 + 边
│   ├── supervisor.py   路由节点（结构化输出选择专家/结束/澄清）
│   ├── state.py        GraphState (TypedDict)
│   ├── handoffs.py     handoff/Command 辅助
│   └── specialists/
│       ├── tax.py
│       ├── visa.py
│       └── ward_office.py
├── rag/                检索
│   ├── ingest.py       加载 md → chunk → 写入 ES + Qdrant（幂等 upsert）
│   ├── chunking.py     按 markdown 标题分块 + overlap
│   ├── embeddings.py   BGE-m3 编码器（单例）
│   ├── es_store.py     ElasticSearch BM25 + kuromoji
│   ├── qdrant_store.py Qdrant 稠密向量
│   ├── hybrid.py       并行查询两库 + RRF 融合
│   ├── rerank.py       bge-reranker cross-encoder 精排
│   └── retriever.py    HybridRetriever + search_knowledge_base @tool
├── tools/              领域工具（LangChain @tool）
│   ├── tax_tools.py    个税估算 / furusato 额度 / 截止日（移植自现有）
│   ├── visa_tools.py   资格判定 / 续签材料清单 / 时限
│   └── ward_office_tools.py  转入届流程 / My Number / 时限
├── knowledge/          源 markdown 知识库
│   ├── tax/            复用现有 data/raw/tax/*.md
│   ├── visa/           新写
│   └── ward_office/    新写
├── eval/
│   ├── datasets/       {tax,visa,ward_office}.jsonl 评测 QA
│   └── run_eval.py     recall@k / MRR + 可选 LLM-judge
├── core/
│   ├── config.py       pydantic-settings 配置
│   ├── llm.py          ChatDeepSeek 工厂（可切换提供商）
│   └── i18n.py         语言检测（EN/JA）
├── tests/              pytest
├── docker-compose.yml  es + qdrant + api
├── Dockerfile          api 镜像
├── Makefile            install / ingest / serve / eval / test
├── README.md
├── .env.example        DEEPSEEK_API_KEY 等
└── pyproject.toml
```

---

## 6. 检索流水线（核心）

### 6.1 索引（ingest.py）
1. 遍历 `knowledge/<domain>/*.md`
2. **分块**：按 markdown 标题层级切，目标 ~512 token，overlap ~64；每块带 metadata：`domain, doc_title, section_path, source_url, language, doc_id, chunk_id`
3. **写 Qdrant**：BGE-m3 编码为 1024 维向量，存入单一 collection `japanlife_kb`，payload 含上述 metadata（`domain` 可过滤）
4. **写 ES**：单一 index `japanlife_kb`，mapping 含 `content`（standard 分析器）与 `content.ja`（kuromoji 子字段）多字段；`domain` 为 keyword
5. **幂等**：以 `chunk_id`（doc_id+序号 hash）为主键 upsert，可重复跑

### 6.2 查询（hybrid.py + rerank.py）
1. 输入：`query`、可选 `domain` 过滤、可选 `language`、`top_k`
2. **ES BM25**：`multi_match` 查 `content` 与 `content.ja`，取 top-K（默认 20），可按 `domain` filter
3. **Qdrant 向量**：BGE-m3 编码 query → 向量检索 top-K（默认 20），可按 `domain` filter
4. **RRF 融合**：`score(d) = Σ_i 1/(k + rank_i(d))`，k=60；合并两路排名
5. **Cross-encoder 精排**：对融合后 top-20 候选用 bge-reranker-v2-m3 重排，取 top-N（默认 5）
6. 输出 `RetrievedChunk(text, metadata, score, citation)` 列表；`citation = doc_title | section_path | source_url`

### 6.3 接口
```python
class HybridRetriever:
    def search(self, query: str, domain: str | None = None,
               language: str | None = None, top_k: int = 5) -> list[RetrievedChunk]: ...
```
封装为 LangChain 工具 `search_knowledge_base(query, domain="", language="", top_k=5) -> {context, citations, result_count}`，供各专家调用。

### 6.4 降级
- ES 不可用 → 仅用 Qdrant（反之亦然），记日志，结果标注 degraded
- 两库均空 → 返回"知识库未覆盖"信号，专家给通用提示 + 免责声明

---

## 7. 多智能体编排

### 7.1 状态
```python
class GraphState(TypedDict):
    messages: Annotated[list[AnyMessage], add_messages]
    user_language: str            # 'en' | 'ja'
    active_domain: str | None     # tax | visa | ward_office
    procedure: dict | None        # 多步流程进度（步骤、已完成项）
    citations: list[dict]         # 本轮引用，回传给 API
```

### 7.2 节点
- **supervisor**：DeepSeek 结构化输出，决定 `route ∈ {tax, visa, ward_office, clarify, finish}`；负责语言检测写入 `user_language`
- **tax / visa / ward_office**：各为 `create_react_agent` 风格子图，挂载本域 `@tool` + `search_knowledge_base`（默认按本域过滤检索）
- 专家答完 → 回到 supervisor → supervisor 判定 `finish`（END）或继续

### 7.3 Handoff（协作亮点）
`ward_office` 专家在识别到跨域后续时，发出 `Command(goto=..., update=...)`：
- 完成「転入届」→ 提示并交接 `visa`（14 天内更新在留卡地址）
- 涉及住民税登记 → 交接 `tax`

用 LangGraph `Command` 实现，supervisor 在交接返回后收口。需做**防环**（记录已访问域，限制单轮 handoff 跳数）。

### 7.4 持久化
`SqliteSaver` checkpointer，`thread_id` 来自 API；保存 `messages / procedure / active_domain`，支持多轮续聊与流程恢复。

---

## 8. 数据流（一次问答）

1. `POST /chat {thread_id?, message}` → 无 thread_id 则新建
2. 图入口：检测语言写入 state
3. supervisor 路由到专家
4. 专家 ReAct：按需调用工具（计算器）+ `search_knowledge_base`（混合检索）
5. 检索：BGE-m3 编码 → Qdrant ∥ ES → RRF → rerank → 带引用 top-N
6. 专家组织答案（附 citations）；必要时 `Command` 交接
7. 回 supervisor → 收尾
8. 返回 `{reply, citations, thread_id, route}`；state 经 checkpointer 持久化

---

## 9. API 设计

| 端点 | 方法 | 入参 | 出参 |
|---|---|---|---|
| `/chat` | POST | `{thread_id?: str, message: str}` | `{reply, citations[], thread_id, route}` |
| `/chat/stream` | POST | 同上 | SSE token 流（`data: {...}`），末包含 citations |
| `/health` | GET | — | `{status, es, qdrant, db}` 各依赖可达性 |

Schema 用 Pydantic；`/docs` 自动可交互演示。

---

## 10. 错误处理与健壮性

- 检索库单点故障 → 降级（见 6.4）
- LLM/工具异常 → 捕获 → 友好提示，不中断会话
- 检索为空 → 明确告知未覆盖 + 通用提示 + 免责声明（税务/法律类必加）
- ingest 幂等可重跑
- handoff 防环（限制单轮跳数 + 已访问集合）

---

## 11. 配置与部署

### 环境变量（`.env.example`）
```
DEEPSEEK_API_KEY=...
LLM_MODEL=deepseek-chat
ES_URL=http://elasticsearch:9200
QDRANT_URL=http://qdrant:6333
EMBEDDING_MODEL=BAAI/bge-m3
RERANKER_MODEL=BAAI/bge-reranker-v2-m3
CHECKPOINT_DB=./japanlife.db
```

### docker-compose 服务
- **elasticsearch**：需含 `analysis-kuromoji` 插件（自定义镜像或 init 安装）
- **qdrant**：官方镜像
- **api**：FastAPI 镜像；启动前/独立 job 执行 `make ingest`

### Makefile 目标
`install / ingest / serve / eval / test / clean`

---

## 12. 测试与评测

### 单元测试（pytest）
- 税务/visa/ward_office 计算器（确定性断言）
- RRF 融合排序正确性
- chunking 切分与 metadata
- 语言检测

### 集成测试
- 图 smoke test（mock LLM，验证路由 + handoff 路径）
- retriever 打一个小种子索引，验证混合检索返回

### RAG 评测（eval/run_eval.py）
- 数据集：每域精选 QA（`question` + `relevant_doc_ids` / 参考答案）
- **检索指标**：Recall@k、MRR；对比 **hybrid vs qdrant-only vs es-only**（输出混合检索的提升幅度——简历硬指标）
- **答案指标（可选）**：LLM-as-judge 评忠实度/相关性

---

## 13. 复用与迁移

| 处理 | 内容 |
|---|---|
| **复用** | `data/raw/tax/*.md` → `knowledge/tax/`；现有税务计算器 → `tools/tax_tools.py`（改成 `@tool`） |
| **新写** | visa / ward_office 的知识 md 与工具 |
| **移除** | Google ADK、ChromaDB、MCP 占位、旧 `japan_life/` 框架层 |

---

## 14. 风险与权衡

- **双存储复杂度**：ES + Qdrant 需同时灌数据、docker 编排——对生产是成本，对作品集是加分（多组件基础设施能力）。
- **ES 日文分词**：依赖 kuromoji 插件，需在镜像层安装。
- **本地模型体积**：BGE-m3 + reranker 首次下载较大；README 说明，必要时提供轻量 fallback（如 `bge-small`）。
- **deepseek-reasoner 工具调用不稳**：带工具的专家节点统一用 `deepseek-chat`；reasoner 仅用于纯推理节点（如有）。

---

## 15. 未来扩展（本期之外）

- 补齐其余 4 个领域
- Streamlit / 前端演示页 + GitHub Actions CI
- Postgres checkpointer + 鉴权 + 限流
- 检索观测（latency、命中分布）与缓存
- 云端部署
