# JapanLife Plan 1 — 检索地基 Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 搭建可独立运行、可测召回率的混合检索 RAG 地基：把 markdown 知识切块后同时写入 ElasticSearch(BM25+kuromoji) 与 Qdrant(BGE-m3 向量)，查询时 RRF 融合 + cross-encoder 精排，并提供评测脚本与 docker。

**Architecture:** 顶层多包应用（`core/ rag/ knowledge/ eval/ tests/`，poetry `package-mode=false`）。`rag/` 内每个文件单一职责：chunking / embeddings / es_store / qdrant_store / hybrid(RRF) / rerank / retriever / ingest。检索走 `HybridRetriever.search()`，对外暴露纯函数 `search_knowledge_base()`（Plan 2 再包成 LangChain @tool）。

**Tech Stack:** Python 3.11, Poetry, pydantic-settings, elasticsearch 8, qdrant-client, sentence-transformers(BGE-m3 + bge-reranker-v2-m3), pytest, docker-compose。

参考规格：`docs/superpowers/specs/2026-06-09-japanlife-langgraph-refactor-design.md`（第 5、6、11、12 节）。

---

## File Structure (Plan 1 范围)

| 文件 | 职责 |
|---|---|
| `pyproject.toml` | 重写为新应用，新增 Plan 1 依赖 |
| `.env.example` | 环境变量样例 |
| `core/config.py` | pydantic-settings 集中配置 |
| `core/i18n.py` | 语言检测 EN/JA |
| `rag/chunking.py` | markdown 按标题分块 + overlap |
| `rag/embeddings.py` | BGE-m3 编码（单例） |
| `rag/qdrant_store.py` | Qdrant 向量库封装 |
| `rag/es_store.py` | ElasticSearch BM25 + kuromoji 封装 |
| `rag/hybrid.py` | RRF 融合（纯函数） |
| `rag/rerank.py` | bge-reranker cross-encoder 精排 |
| `rag/retriever.py` | HybridRetriever + search_knowledge_base |
| `rag/ingest.py` | 加载→切块→写两库（幂等） |
| `knowledge/{tax,visa,ward_office}/*.md` | 源知识 |
| `eval/metrics.py` | recall@k / MRR 纯函数 |
| `eval/run_eval.py` | 混合 vs 基线对比报告 |
| `eval/datasets/*.jsonl` | 评测 QA |
| `docker/elasticsearch/Dockerfile` | ES + kuromoji 自定义镜像 |
| `docker-compose.yml` | es + qdrant 服务 |
| `Makefile` | install/ingest/eval/test |
| `tests/**` | 单测 + 集成测试 |

---

## Task 1: 项目脚手架与依赖

**Files:**
- Modify: `pyproject.toml`（整体替换）
- Create: `core/__init__.py`, `rag/__init__.py`, `eval/__init__.py`, `tests/__init__.py`, `.env.example`
- Delete: 旧框架 `japan_life/`, 顶层 `rag/`(旧), `mcp_servers/`, `api/`

- [ ] **Step 1: 删除旧框架包，避免与新包冲突**

```bash
cd /Users/javagod/VsCodeProjects/JapanLife
rm -rf japan_life mcp_servers api rag
```
（保留 `data/` 作为 tax 知识来源，Task 5 移植后再删。）

- [ ] **Step 2: 用新内容整体替换 `pyproject.toml`**

```toml
[tool.poetry]
name = "japanlife"
version = "0.2.0"
description = "Hybrid-RAG multi-agent assistant for foreigners living in Japan"
authors = ["javagod"]
readme = "README.md"
package-mode = false

[tool.poetry.dependencies]
python = "^3.11"
pydantic-settings = "^2.5.0"
elasticsearch = "^8.15.0"
qdrant-client = "^1.12.0"
sentence-transformers = "^3.3.0"
numpy = ">=1.26"

[tool.poetry.group.dev.dependencies]
pytest = "^8.0.0"

[build-system]
requires = ["poetry-core"]
build-backend = "poetry.core.masonry.api"

[tool.pytest.ini_options]
pythonpath = ["."]
testpaths = ["tests"]
markers = [
    "integration: requires running ES/Qdrant services or model downloads",
]
```

- [ ] **Step 3: 创建空包标记与环境样例**

```bash
mkdir -p core rag eval tests knowledge/tax knowledge/visa knowledge/ward_office eval/datasets
touch core/__init__.py rag/__init__.py eval/__init__.py tests/__init__.py
```

`.env.example`:
```
# LLM (Plan 2 起使用)
DEEPSEEK_API_KEY=your-key-here
LLM_MODEL=deepseek-chat

# Retrieval infra
ES_URL=http://localhost:9200
QDRANT_URL=http://localhost:6333
INDEX_NAME=japanlife_kb

# Local models
EMBEDDING_MODEL=BAAI/bge-m3
RERANKER_MODEL=BAAI/bge-reranker-v2-m3
EMBEDDING_DIM=1024
```

- [ ] **Step 4: 安装依赖**

Run: `poetry install`
Expected: 安装成功（sentence-transformers 会带 torch，首次较慢）。

- [ ] **Step 5: 提交**

```bash
git add -A
git commit -m "chore: scaffold japanlife app, drop old ADK framework"
```

---

## Task 2: 配置模块 `core/config.py`

**Files:**
- Create: `core/config.py`
- Test: `tests/test_config.py`

- [ ] **Step 1: 写失败测试**

`tests/test_config.py`:
```python
from core.config import Settings


def test_defaults_without_env_file():
    s = Settings(_env_file=None)
    assert s.index_name == "japanlife_kb"
    assert s.embedding_dim == 1024
    assert s.rrf_k == 60


def test_override_via_kwargs():
    s = Settings(_env_file=None, es_url="http://es:9200")
    assert s.es_url == "http://es:9200"
```

- [ ] **Step 2: 运行测试，确认失败**

Run: `poetry run pytest tests/test_config.py -v`
Expected: FAIL（`ModuleNotFoundError: core.config`）

- [ ] **Step 3: 实现 `core/config.py`**

```python
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env", env_file_encoding="utf-8", extra="ignore"
    )

    deepseek_api_key: str = ""
    llm_model: str = "deepseek-chat"

    es_url: str = "http://localhost:9200"
    qdrant_url: str = "http://localhost:6333"
    index_name: str = "japanlife_kb"

    embedding_model: str = "BAAI/bge-m3"
    reranker_model: str = "BAAI/bge-reranker-v2-m3"
    embedding_dim: int = 1024

    retrieval_top_k: int = 20
    rerank_top_n: int = 5
    rrf_k: int = 60

    checkpoint_db: str = "./japanlife.db"


settings = Settings()
```

- [ ] **Step 4: 运行测试，确认通过**

Run: `poetry run pytest tests/test_config.py -v`
Expected: PASS（2 passed）

- [ ] **Step 5: 提交**

```bash
git add core/config.py tests/test_config.py
git commit -m "feat(core): add pydantic settings"
```

---

## Task 3: 语言检测 `core/i18n.py`

**Files:**
- Create: `core/i18n.py`
- Test: `tests/test_i18n.py`

- [ ] **Step 1: 写失败测试**

`tests/test_i18n.py`:
```python
from core.i18n import detect_language


def test_japanese_text():
    assert detect_language("確定申告について教えてください") == "ja"


def test_english_text():
    assert detect_language("How do I file my taxes?") == "en"


def test_empty_is_english():
    assert detect_language("") == "en"


def test_mixed_with_japanese_majority():
    assert detect_language("e-Taxの使い方") == "ja"
```

- [ ] **Step 2: 运行测试，确认失败**

Run: `poetry run pytest tests/test_i18n.py -v`
Expected: FAIL（`ModuleNotFoundError: core.i18n`）

- [ ] **Step 3: 实现 `core/i18n.py`**

```python
import re

_JA_PATTERN = re.compile(r"[\u3040-\u30ff\u3400-\u4dbf\u4e00-\u9fff\uff66-\uff9f]")


def detect_language(text: str) -> str:
    """Return 'ja' if Japanese characters are a meaningful share of the text, else 'en'."""
    if not text:
        return "en"
    non_space = re.sub(r"\s", "", text)
    if not non_space:
        return "en"
    ja_chars = _JA_PATTERN.findall(non_space)
    return "ja" if len(ja_chars) / len(non_space) >= 0.2 else "en"
```

- [ ] **Step 4: 运行测试，确认通过**

Run: `poetry run pytest tests/test_i18n.py -v`
Expected: PASS（4 passed）

- [ ] **Step 5: 提交**

```bash
git add core/i18n.py tests/test_i18n.py
git commit -m "feat(core): add EN/JA language detection"
```

---

## Task 4: Markdown 分块 `rag/chunking.py`

**Files:**
- Create: `rag/chunking.py`
- Test: `tests/test_chunking.py`

- [ ] **Step 1: 写失败测试**

`tests/test_chunking.py`:
```python
from rag.chunking import Chunk, chunk_markdown

MD = """# 税务指南

## 确定申告
确定申告是日本的年度个人所得税申报。

## ふるさと納税
ふるさと納税是一种向地方政府捐款的制度。
"""


def test_splits_by_section():
    chunks = chunk_markdown(MD, {"doc_id": "tax/guide.md"})
    paths = [c.metadata["section_path"] for c in chunks]
    assert "税务指南 > 确定申告" in paths
    assert "税务指南 > ふるさと納税" in paths


def test_long_section_splits_with_overlap():
    body = "あ" * 3000
    md = f"# T\n## S\n{body}"
    chunks = chunk_markdown(md, {"doc_id": "d"}, max_chars=1000, overlap=100)
    assert len(chunks) >= 3
    # 相邻块有 overlap：前块尾部出现在后块头部
    assert chunks[0].text[-50:] in chunks[1].text


def test_chunk_id_is_deterministic_and_unique():
    chunks = chunk_markdown(MD, {"doc_id": "tax/guide.md"})
    ids = [c.chunk_id for c in chunks]
    assert len(ids) == len(set(ids))
    again = chunk_markdown(MD, {"doc_id": "tax/guide.md"})
    assert ids == [c.chunk_id for c in again]


def test_metadata_is_preserved():
    chunks = chunk_markdown(MD, {"doc_id": "tax/guide.md", "domain": "tax"})
    assert all(c.metadata["domain"] == "tax" for c in chunks)
```

- [ ] **Step 2: 运行测试，确认失败**

Run: `poetry run pytest tests/test_chunking.py -v`
Expected: FAIL（`ModuleNotFoundError: rag.chunking`）

- [ ] **Step 3: 实现 `rag/chunking.py`**

```python
from __future__ import annotations

import hashlib
import re
from dataclasses import dataclass, field

_HEADER_RE = re.compile(r"^(#{1,6})\s+(.*)$")


@dataclass
class Chunk:
    text: str
    metadata: dict = field(default_factory=dict)

    @property
    def chunk_id(self) -> str:
        base = "::".join(
            [
                str(self.metadata.get("doc_id", "")),
                str(self.metadata.get("section_path", "")),
                str(self.metadata.get("chunk_index", 0)),
            ]
        )
        return hashlib.sha1(base.encode("utf-8")).hexdigest()


def _split_sections(markdown: str) -> list[tuple[str, str]]:
    sections: list[tuple[str, str]] = []
    stack: list[str] = []
    buf: list[str] = []
    path = ""

    def flush() -> None:
        nonlocal buf
        body = "\n".join(buf).strip()
        if body:
            sections.append((path, body))
        buf = []

    for line in markdown.splitlines():
        m = _HEADER_RE.match(line)
        if m:
            flush()
            level = len(m.group(1))
            title = m.group(2).strip()
            stack[:] = stack[: level - 1]
            while len(stack) < level - 1:
                stack.append("")
            stack.append(title)
            path = " > ".join(s for s in stack if s)
        else:
            buf.append(line)
    flush()
    return sections


def chunk_markdown(
    markdown: str,
    metadata: dict,
    max_chars: int = 1200,
    overlap: int = 150,
) -> list[Chunk]:
    chunks: list[Chunk] = []
    idx = 0
    for section_path, body in _split_sections(markdown):
        start = 0
        while start < len(body):
            piece = body[start : start + max_chars].strip()
            meta = {**metadata, "section_path": section_path, "chunk_index": idx}
            chunks.append(Chunk(text=piece, metadata=meta))
            idx += 1
            if start + max_chars >= len(body):
                break
            start += max_chars - overlap
    return chunks
```

- [ ] **Step 4: 运行测试，确认通过**

Run: `poetry run pytest tests/test_chunking.py -v`
Expected: PASS（4 passed）

- [ ] **Step 5: 提交**

```bash
git add rag/chunking.py tests/test_chunking.py
git commit -m "feat(rag): markdown header-aware chunking"
```

---

## Task 5: 知识内容 `knowledge/`

**Files:**
- Create: `knowledge/tax/*.md`（移植）, `knowledge/visa/01-visa-types.md`, `knowledge/visa/02-renewal.md`, `knowledge/ward_office/01-moving-in.md`, `knowledge/ward_office/02-my-number.md`
- Delete: `data/`（移植后）

- [ ] **Step 1: 移植 tax 知识**

```bash
cp data/raw/tax/*.md knowledge/tax/
ls knowledge/tax
```
Expected: 列出 7 个 md 文件。

- [ ] **Step 2: 写 `knowledge/visa/01-visa-types.md`**

```markdown
# Visa Types for Foreign Residents in Japan

## Work Visa (就労ビザ)
The Engineer/Specialist in Humanities/International Services visa (技術・人文知識・国際業務)
is the most common work status. It requires a job offer matching your degree or experience.
Validity is typically 1, 3, or 5 years and is tied to your employer.

## Permanent Residency (永住)
Permanent residency (永住権) generally requires 10 continuous years in Japan, with at least
5 years on a work visa. Holders of the Highly Skilled Professional visa may apply after 1-3 years.
You must show stable income, tax/pension payment records, and good conduct.

## Dependent Visa (家族滞在)
The Dependent visa (家族滞在) is for spouses and children of work-visa holders. Dependents may
work up to 28 hours/week only after obtaining permission to engage in activities other than
those permitted (資格外活動許可).
```

- [ ] **Step 3: 写 `knowledge/visa/02-renewal.md`**

```markdown
# Visa Renewal and Change of Status

## Renewal (在留期間更新)
Apply to renew your residence status at the Immigration Bureau (入管) up to 3 months before
expiry. Required documents: application form, passport, residence card (在留カード), a photo,
and proof of employment and tax payment. Processing takes 2 weeks to 1 month.

## Change of Status (在留資格変更)
To change your status (e.g., from Student to Engineer), file a Change of Status of Residence
application. Do not start the new activity until approval. Overstaying or working outside your
status can lead to denial of future applications.

## Address Change (住居地変更届)
After moving, you must report your new address. Register it at the ward office within 14 days;
this also updates the address on your residence card.
```

- [ ] **Step 4: 写 `knowledge/ward_office/01-moving-in.md`**

```markdown
# Moving In: Ward Office Procedures (転入届)

## Moving-in Notification (転入届)
Within 14 days of moving to a new municipality, submit a moving-in notification (転入届) at the
ward or city office (区役所・市役所). Bring your residence card and, if moving from another
Japanese municipality, the moving-out certificate (転出証明書) from your previous city.

## Resident Record (住民票)
After registration you can obtain a resident certificate (住民票), needed for opening bank
accounts, signing phone/utility contracts, and many official procedures.

## What Registration Triggers
Registering your address also enrolls you for National Health Insurance (国民健康保険) and the
National Pension (国民年金) if you are not on employer-based insurance, and it is the basis for
resident tax (住民税).
```

- [ ] **Step 5: 写 `knowledge/ward_office/02-my-number.md`**

```markdown
# My Number (マイナンバー)

## What Is My Number
My Number (個人番号) is a 12-digit ID assigned to every resident, used for tax, social security,
and disaster response. A notification is mailed to your registered address after you complete
your moving-in notification.

## My Number Card (マイナンバーカード)
You can apply for a physical My Number Card online, by mail, or at the ward office. The card
serves as photo ID and enables online tax filing (e-Tax) and access to administrative services.

## When You Need It
Employers, banks, and securities firms require your My Number for tax withholding and reporting.
Keep it confidential and only share it through official channels.
```

- [ ] **Step 6: 删除已移植的 `data/`**

```bash
rm -rf data
```

- [ ] **Step 7: 提交**

```bash
git add knowledge
git commit -m "content: port tax knowledge + add visa & ward_office docs"
```

---

## Task 6: 向量编码 `rag/embeddings.py`

**Files:**
- Create: `rag/embeddings.py`
- Test: `tests/test_embeddings.py`（标记 integration，需下载模型）

- [ ] **Step 1: 写失败测试**

`tests/test_embeddings.py`:
```python
import pytest

from core.config import settings
from rag.embeddings import embed_query, embed_texts


@pytest.mark.integration
def test_embed_query_dim():
    vec = embed_query("How do I file taxes in Japan?")
    assert len(vec) == settings.embedding_dim


@pytest.mark.integration
def test_embed_texts_batch():
    vecs = embed_texts(["確定申告", "permanent residency"])
    assert len(vecs) == 2
    assert all(len(v) == settings.embedding_dim for v in vecs)
```

- [ ] **Step 2: 运行测试，确认失败（收集错误即可）**

Run: `poetry run pytest tests/test_embeddings.py -v`
Expected: FAIL（`ModuleNotFoundError: rag.embeddings`）

- [ ] **Step 3: 实现 `rag/embeddings.py`**

```python
from __future__ import annotations

from functools import lru_cache

from sentence_transformers import SentenceTransformer

from core.config import settings


@lru_cache(maxsize=1)
def get_embedder() -> SentenceTransformer:
    return SentenceTransformer(settings.embedding_model)


def embed_texts(texts: list[str]) -> list[list[float]]:
    model = get_embedder()
    vectors = model.encode(texts, normalize_embeddings=True)
    return [v.tolist() for v in vectors]


def embed_query(text: str) -> list[float]:
    return embed_texts([text])[0]
```

- [ ] **Step 4: 运行集成测试，确认通过（首次会下载 BGE-m3）**

Run: `poetry run pytest tests/test_embeddings.py -v -m integration`
Expected: PASS（2 passed；下载耗时较长）

- [ ] **Step 5: 提交**

```bash
git add rag/embeddings.py tests/test_embeddings.py
git commit -m "feat(rag): BGE-m3 embedding wrapper"
```

---

## Task 7: Qdrant 存储 `rag/qdrant_store.py`

**Files:**
- Create: `rag/qdrant_store.py`
- Test: `tests/test_qdrant_store.py`（用 `:memory:` 客户端，无需服务）

- [ ] **Step 1: 写失败测试**

`tests/test_qdrant_store.py`:
```python
import pytest
from qdrant_client import QdrantClient

from core.config import settings
from rag.qdrant_store import QdrantStore, point_id


@pytest.fixture
def store(monkeypatch):
    monkeypatch.setattr(settings, "embedding_dim", 4)
    s = QdrantStore(client=QdrantClient(":memory:"), collection="test_kb")
    s.ensure_collection()
    return s


def test_point_id_is_stable():
    assert point_id("abc") == point_id("abc")


def test_upsert_and_search_returns_nearest(store):
    store.upsert(
        ids=["a", "b"],
        vectors=[[1.0, 0.0, 0.0, 0.0], [0.0, 1.0, 0.0, 0.0]],
        payloads=[{"domain": "tax", "content": "A"}, {"domain": "visa", "content": "B"}],
    )
    hits = store.search([0.9, 0.1, 0.0, 0.0], top_k=1)
    assert hits[0][0] == "a"


def test_domain_filter(store):
    store.upsert(
        ids=["a", "b"],
        vectors=[[1.0, 0.0, 0.0, 0.0], [0.9, 0.1, 0.0, 0.0]],
        payloads=[{"domain": "tax", "content": "A"}, {"domain": "visa", "content": "B"}],
    )
    hits = store.search([1.0, 0.0, 0.0, 0.0], top_k=5, domain="visa")
    assert [h[0] for h in hits] == ["b"]
```

- [ ] **Step 2: 运行测试，确认失败**

Run: `poetry run pytest tests/test_qdrant_store.py -v`
Expected: FAIL（`ModuleNotFoundError: rag.qdrant_store`）

- [ ] **Step 3: 实现 `rag/qdrant_store.py`**

```python
from __future__ import annotations

import uuid

from qdrant_client import QdrantClient
from qdrant_client.models import (
    Distance,
    FieldCondition,
    Filter,
    MatchValue,
    PointStruct,
    VectorParams,
)

from core.config import settings


def point_id(chunk_id: str) -> str:
    return str(uuid.uuid5(uuid.NAMESPACE_URL, chunk_id))


class QdrantStore:
    def __init__(self, client: QdrantClient | None = None, collection: str | None = None):
        self.client = client or QdrantClient(url=settings.qdrant_url)
        self.collection = collection or settings.index_name

    def ensure_collection(self) -> None:
        if not self.client.collection_exists(self.collection):
            self.client.create_collection(
                collection_name=self.collection,
                vectors_config=VectorParams(
                    size=settings.embedding_dim, distance=Distance.COSINE
                ),
            )

    def upsert(
        self, ids: list[str], vectors: list[list[float]], payloads: list[dict]
    ) -> None:
        points = [
            PointStruct(id=point_id(cid), vector=vec, payload={**pl, "chunk_id": cid})
            for cid, vec, pl in zip(ids, vectors, payloads)
        ]
        self.client.upsert(collection_name=self.collection, points=points)

    def search(
        self, vector: list[float], top_k: int, domain: str | None = None
    ) -> list[tuple[str, float, dict]]:
        flt = None
        if domain:
            flt = Filter(
                must=[FieldCondition(key="domain", match=MatchValue(value=domain))]
            )
        res = self.client.query_points(
            collection_name=self.collection,
            query=vector,
            limit=top_k,
            query_filter=flt,
            with_payload=True,
        )
        return [(p.payload["chunk_id"], p.score, p.payload) for p in res.points]
```

- [ ] **Step 4: 运行测试，确认通过**

Run: `poetry run pytest tests/test_qdrant_store.py -v`
Expected: PASS（4 passed）

- [ ] **Step 5: 提交**

```bash
git add rag/qdrant_store.py tests/test_qdrant_store.py
git commit -m "feat(rag): Qdrant vector store"
```

---

## Task 8: ElasticSearch 存储 `rag/es_store.py`

**Files:**
- Create: `rag/es_store.py`, `tests/conftest.py`
- Test: `tests/test_es_store.py`（集成测试，ES 不可达则跳过）

- [ ] **Step 1: 写共享 fixture `tests/conftest.py`**

```python
import pytest
from elasticsearch import Elasticsearch

from core.config import settings


@pytest.fixture(scope="session")
def es_client():
    client = Elasticsearch(hosts=[settings.es_url])
    try:
        if not client.ping():
            pytest.skip("ElasticSearch not reachable")
    except Exception:
        pytest.skip("ElasticSearch not reachable")
    return client
```

- [ ] **Step 2: 写失败测试 `tests/test_es_store.py`**

```python
import uuid

import pytest

from rag.es_store import ESStore


@pytest.mark.integration
def test_index_and_search(es_client):
    index = f"test_kb_{uuid.uuid4().hex[:8]}"
    store = ESStore(client=es_client, index=index)
    store.ensure_index()
    try:
        store.index_chunks(
            ids=["a", "b"],
            texts=["確定申告 is the annual tax return", "permanent residency requires 10 years"],
            payloads=[{"domain": "tax"}, {"domain": "visa"}],
        )
        hits = store.search("確定申告", top_k=5)
        assert hits and hits[0][0] == "a"
        filtered = store.search("residency", top_k=5, domain="visa")
        assert [h[0] for h in filtered] == ["b"]
    finally:
        es_client.indices.delete(index=index, ignore_unavailable=True)
```

- [ ] **Step 3: 运行测试，确认失败**

Run: `poetry run pytest tests/test_es_store.py -v`
Expected: FAIL（`ModuleNotFoundError: rag.es_store`；若 ES 未起则该用例 skip——先让导入失败）

- [ ] **Step 4: 实现 `rag/es_store.py`**

```python
from __future__ import annotations

from elasticsearch import Elasticsearch
from elasticsearch.helpers import bulk

from core.config import settings

INDEX_BODY = {
    "settings": {
        "analysis": {
            "analyzer": {
                "ja_analyzer": {"type": "custom", "tokenizer": "kuromoji_tokenizer"}
            }
        }
    },
    "mappings": {
        "properties": {
            "content": {
                "type": "text",
                "analyzer": "standard",
                "fields": {"ja": {"type": "text", "analyzer": "ja_analyzer"}},
            },
            "domain": {"type": "keyword"},
            "doc_id": {"type": "keyword"},
            "doc_title": {"type": "keyword"},
            "section_path": {"type": "keyword"},
            "source_url": {"type": "keyword"},
            "language": {"type": "keyword"},
            "chunk_id": {"type": "keyword"},
        }
    },
}


class ESStore:
    def __init__(self, client: Elasticsearch | None = None, index: str | None = None):
        self.client = client or Elasticsearch(hosts=[settings.es_url])
        self.index = index or settings.index_name

    def ensure_index(self) -> None:
        if not self.client.indices.exists(index=self.index):
            self.client.indices.create(
                index=self.index,
                settings=INDEX_BODY["settings"],
                mappings=INDEX_BODY["mappings"],
            )

    def index_chunks(
        self, ids: list[str], texts: list[str], payloads: list[dict]
    ) -> None:
        actions = [
            {
                "_index": self.index,
                "_id": cid,
                "_source": {"content": txt, "chunk_id": cid, **pl},
            }
            for cid, txt, pl in zip(ids, texts, payloads)
        ]
        bulk(self.client, actions)
        self.client.indices.refresh(index=self.index)

    def search(
        self, query: str, top_k: int, domain: str | None = None
    ) -> list[tuple[str, float, dict]]:
        bool_q: dict = {
            "must": [
                {"multi_match": {"query": query, "fields": ["content", "content.ja"]}}
            ]
        }
        if domain:
            bool_q["filter"] = [{"term": {"domain": domain}}]
        res = self.client.search(index=self.index, query={"bool": bool_q}, size=top_k)
        return [
            (hit["_source"]["chunk_id"], hit["_score"], hit["_source"])
            for hit in res["hits"]["hits"]
        ]
```

- [ ] **Step 5: 起 ES（见 Task 14 的 compose；此处可先单独起），运行集成测试**

Run: `poetry run pytest tests/test_es_store.py -v -m integration`
Expected: PASS（ES 在跑则 1 passed；未起则 skipped）

- [ ] **Step 6: 提交**

```bash
git add rag/es_store.py tests/conftest.py tests/test_es_store.py
git commit -m "feat(rag): ElasticSearch BM25 + kuromoji store"
```

---

## Task 9: RRF 融合 `rag/hybrid.py`

**Files:**
- Create: `rag/hybrid.py`
- Test: `tests/test_hybrid.py`

- [ ] **Step 1: 写失败测试**

`tests/test_hybrid.py`:
```python
from rag.hybrid import fuse, reciprocal_rank_fusion


def test_rrf_scores_first_rank_highest():
    scores = reciprocal_rank_fusion([["a", "b", "c"]], k=60)
    assert scores["a"] > scores["b"] > scores["c"]
    assert scores["a"] == 1 / 61


def test_rrf_rewards_appearing_in_both_lists():
    scores = reciprocal_rank_fusion([["a", "b"], ["b", "a"]], k=60)
    # b: 1/62 + 1/61 ; a: 1/61 + 1/62 -> equal; both beat a single-list doc
    assert round(scores["a"], 6) == round(scores["b"], 6)


def test_fuse_merges_payloads_and_orders():
    es_hits = [("a", 9.0, {"content": "A"}), ("c", 5.0, {"content": "C"})]
    qd_hits = [("a", 0.9, {"content": "A"}), ("b", 0.8, {"content": "B"})]
    fused = fuse(es_hits, qd_hits, k=60)
    ids = [cid for cid, _, _ in fused]
    assert ids[0] == "a"  # 在两路都排第一
    assert set(ids) == {"a", "b", "c"}
    payload_a = next(pl for cid, _, pl in fused if cid == "a")
    assert payload_a["content"] == "A"
```

- [ ] **Step 2: 运行测试，确认失败**

Run: `poetry run pytest tests/test_hybrid.py -v`
Expected: FAIL（`ModuleNotFoundError: rag.hybrid`）

- [ ] **Step 3: 实现 `rag/hybrid.py`**

```python
from __future__ import annotations


def reciprocal_rank_fusion(
    rankings: list[list[str]], k: int = 60
) -> dict[str, float]:
    scores: dict[str, float] = {}
    for ranking in rankings:
        for rank, doc_id in enumerate(ranking):
            scores[doc_id] = scores.get(doc_id, 0.0) + 1.0 / (k + rank + 1)
    return scores


def fuse(
    es_hits: list[tuple[str, float, dict]],
    qdrant_hits: list[tuple[str, float, dict]],
    k: int = 60,
) -> list[tuple[str, float, dict]]:
    payloads: dict[str, dict] = {}
    for cid, _, pl in [*es_hits, *qdrant_hits]:
        payloads.setdefault(cid, pl)
    es_ranking = [cid for cid, _, _ in es_hits]
    qd_ranking = [cid for cid, _, _ in qdrant_hits]
    fused = reciprocal_rank_fusion([es_ranking, qd_ranking], k=k)
    ordered = sorted(fused.items(), key=lambda x: x[1], reverse=True)
    return [(cid, score, payloads[cid]) for cid, score in ordered]
```

- [ ] **Step 4: 运行测试，确认通过**

Run: `poetry run pytest tests/test_hybrid.py -v`
Expected: PASS（3 passed）

- [ ] **Step 5: 提交**

```bash
git add rag/hybrid.py tests/test_hybrid.py
git commit -m "feat(rag): RRF hybrid fusion"
```

---

## Task 10: 精排 `rag/rerank.py`

**Files:**
- Create: `rag/rerank.py`
- Test: `tests/test_rerank.py`（monkeypatch 桩，免下载模型）

- [ ] **Step 1: 写失败测试**

`tests/test_rerank.py`:
```python
import rag.rerank as rerank_mod
from rag.rerank import rerank


class _StubReranker:
    def predict(self, pairs):
        # 给含 "match" 的文档更高分
        return [1.0 if "match" in doc else 0.0 for _q, doc in pairs]


def test_rerank_orders_by_cross_encoder(monkeypatch):
    monkeypatch.setattr(rerank_mod, "get_reranker", lambda: _StubReranker())
    candidates = [
        ("a", 0.1, {"content": "no relation"}),
        ("b", 0.2, {"content": "a strong match here"}),
    ]
    out = rerank("query", candidates, top_n=2)
    assert [cid for cid, _, _ in out] == ["b", "a"]


def test_rerank_respects_top_n(monkeypatch):
    monkeypatch.setattr(rerank_mod, "get_reranker", lambda: _StubReranker())
    candidates = [
        ("a", 0.1, {"content": "match"}),
        ("b", 0.2, {"content": "match"}),
        ("c", 0.3, {"content": "x"}),
    ]
    out = rerank("q", candidates, top_n=1)
    assert len(out) == 1


def test_rerank_empty_returns_empty(monkeypatch):
    monkeypatch.setattr(rerank_mod, "get_reranker", lambda: _StubReranker())
    assert rerank("q", [], top_n=3) == []
```

- [ ] **Step 2: 运行测试，确认失败**

Run: `poetry run pytest tests/test_rerank.py -v`
Expected: FAIL（`ModuleNotFoundError: rag.rerank`）

- [ ] **Step 3: 实现 `rag/rerank.py`**

```python
from __future__ import annotations

from functools import lru_cache

from sentence_transformers import CrossEncoder

from core.config import settings


@lru_cache(maxsize=1)
def get_reranker() -> CrossEncoder:
    return CrossEncoder(settings.reranker_model)


def rerank(
    query: str, candidates: list[tuple[str, float, dict]], top_n: int
) -> list[tuple[str, float, dict]]:
    if not candidates:
        return []
    model = get_reranker()
    pairs = [(query, pl.get("content", "")) for _cid, _score, pl in candidates]
    scores = model.predict(pairs)
    ranked = sorted(zip(candidates, scores), key=lambda x: x[1], reverse=True)
    return [(cid, float(score), pl) for (cid, _old, pl), score in ranked[:top_n]]
```

- [ ] **Step 4: 运行测试，确认通过**

Run: `poetry run pytest tests/test_rerank.py -v`
Expected: PASS（3 passed）

- [ ] **Step 5: 提交**

```bash
git add rag/rerank.py tests/test_rerank.py
git commit -m "feat(rag): cross-encoder reranking"
```

---

## Task 11: 混合检索器 `rag/retriever.py`

**Files:**
- Create: `rag/retriever.py`
- Test: `tests/test_retriever.py`（QdrantStore `:memory:` + 假 ESStore + 桩 reranker + monkeypatch 编码）

- [ ] **Step 1: 写失败测试**

`tests/test_retriever.py`:
```python
import pytest
from qdrant_client import QdrantClient

import rag.retriever as retriever_mod
from core.config import settings
from rag.qdrant_store import QdrantStore
from rag.retriever import HybridRetriever, RetrievedChunk


class _FakeES:
    def __init__(self, hits):
        self._hits = hits

    def search(self, query, top_k, domain=None):
        return self._hits


@pytest.fixture
def qdrant(monkeypatch):
    monkeypatch.setattr(settings, "embedding_dim", 4)
    s = QdrantStore(client=QdrantClient(":memory:"), collection="rt_kb")
    s.ensure_collection()
    s.upsert(
        ids=["a", "b"],
        vectors=[[1.0, 0, 0, 0], [0, 1.0, 0, 0]],
        payloads=[
            {"domain": "tax", "content": "tax doc A", "doc_title": "A", "section_path": "S1", "source_url": ""},
            {"domain": "tax", "content": "tax doc B", "doc_title": "B", "section_path": "S2", "source_url": ""},
        ],
    )
    return s


def test_search_returns_reranked_chunks(monkeypatch, qdrant):
    es = _FakeES([("a", 7.0, {"chunk_id": "a", "content": "tax doc A", "doc_title": "A", "section_path": "S1", "source_url": ""})])
    monkeypatch.setattr(retriever_mod, "embed_query", lambda q: [1.0, 0, 0, 0])

    class _Stub:
        def predict(self, pairs):
            return [1.0 if "A" in doc else 0.0 for _q, doc in pairs]

    import rag.rerank as rerank_mod
    monkeypatch.setattr(rerank_mod, "get_reranker", lambda: _Stub())

    r = HybridRetriever(es=es, qdrant=qdrant)
    out = r.search("tax", domain="tax", top_k=5)
    assert isinstance(out[0], RetrievedChunk)
    assert out[0].metadata["chunk_id"] == "a"
    assert out[0].citation == "A | S1"


def test_search_degrades_when_es_raises(monkeypatch, qdrant):
    class _BrokenES:
        def search(self, *a, **k):
            raise RuntimeError("es down")

    monkeypatch.setattr(retriever_mod, "embed_query", lambda q: [0, 1.0, 0, 0])
    import rag.rerank as rerank_mod
    monkeypatch.setattr(rerank_mod, "get_reranker", lambda: type("S", (), {"predict": lambda self, p: [1.0] * len(p)})())

    r = HybridRetriever(es=_BrokenES(), qdrant=qdrant)
    out = r.search("anything", top_k=5)
    assert len(out) >= 1  # 仅靠 Qdrant 仍能返回
```

- [ ] **Step 2: 运行测试，确认失败**

Run: `poetry run pytest tests/test_retriever.py -v`
Expected: FAIL（`ModuleNotFoundError: rag.retriever`）

- [ ] **Step 3: 实现 `rag/retriever.py`**

```python
from __future__ import annotations

from dataclasses import dataclass

from core.config import settings
from rag.embeddings import embed_query
from rag.es_store import ESStore
from rag.hybrid import fuse
from rag.qdrant_store import QdrantStore
from rag.rerank import rerank


@dataclass
class RetrievedChunk:
    text: str
    metadata: dict
    score: float
    citation: str


def _citation(payload: dict) -> str:
    parts = [payload.get("doc_title"), payload.get("section_path"), payload.get("source_url")]
    return " | ".join(p for p in parts if p) or "Unknown source"


class HybridRetriever:
    def __init__(self, es=None, qdrant=None):
        self.es = es or ESStore()
        self.qdrant = qdrant or QdrantStore()

    def search(
        self, query: str, domain: str | None = None, top_k: int | None = None
    ) -> list[RetrievedChunk]:
        top_k = top_k or settings.retrieval_top_k
        try:
            es_hits = self.es.search(query, top_k=top_k, domain=domain)
        except Exception:
            es_hits = []
        try:
            qd_hits = self.qdrant.search(embed_query(query), top_k=top_k, domain=domain)
        except Exception:
            qd_hits = []

        fused = fuse(es_hits, qd_hits, k=settings.rrf_k)
        reranked = rerank(query, fused, top_n=settings.rerank_top_n) if fused else []
        return [
            RetrievedChunk(
                text=pl.get("content", ""),
                metadata=pl,
                score=score,
                citation=_citation(pl),
            )
            for _cid, score, pl in reranked
        ]


def search_knowledge_base(query: str, domain: str = "", top_k: int = 5) -> dict:
    """Plain-function knowledge search; Plan 2 wraps this as a LangChain @tool."""
    results = HybridRetriever().search(query, domain=domain or None)[:top_k]
    context = "\n\n---\n\n".join(
        f"[Source {i}: {r.citation}]\n{r.text}" for i, r in enumerate(results, 1)
    )
    citations = "\n".join(f"[{i}] {r.citation}" for i, r in enumerate(results, 1))
    return {
        "context": context or "No relevant information found in the knowledge base.",
        "citations": citations,
        "result_count": len(results),
    }
```

- [ ] **Step 4: 运行测试，确认通过**

Run: `poetry run pytest tests/test_retriever.py -v`
Expected: PASS（2 passed）

- [ ] **Step 5: 提交**

```bash
git add rag/retriever.py tests/test_retriever.py
git commit -m "feat(rag): hybrid retriever with degradation"
```

---

## Task 12: 入库脚本 `rag/ingest.py`

**Files:**
- Create: `rag/ingest.py`
- Test: `tests/test_ingest_loading.py`（仅测纯函数 load/build，不连服务）

- [ ] **Step 1: 写失败测试**

`tests/test_ingest_loading.py`:
```python
from pathlib import Path

from rag.ingest import build_chunks, load_documents


def test_load_and_build(tmp_path: Path):
    (tmp_path / "tax").mkdir()
    (tmp_path / "tax" / "guide.md").write_text("# T\n## S\nbody text", encoding="utf-8")

    docs = load_documents(tmp_path)
    assert docs and docs[0][0] == "tax"

    chunks = build_chunks(docs)
    assert chunks
    c = chunks[0]
    assert c.metadata["domain"] == "tax"
    assert c.metadata["doc_id"] == "tax/guide.md"
    assert "content" not in c.metadata  # content 在入库时再加
```

- [ ] **Step 2: 运行测试，确认失败**

Run: `poetry run pytest tests/test_ingest_loading.py -v`
Expected: FAIL（`ModuleNotFoundError: rag.ingest`）

- [ ] **Step 3: 实现 `rag/ingest.py`**

```python
from __future__ import annotations

import argparse
from pathlib import Path

from rag.chunking import Chunk, chunk_markdown
from rag.embeddings import embed_texts
from rag.es_store import ESStore
from rag.qdrant_store import QdrantStore

KNOWLEDGE_DIR = Path(__file__).resolve().parent.parent / "knowledge"


def load_documents(base: Path = KNOWLEDGE_DIR) -> list[tuple[str, str, str, str]]:
    docs = []
    for md in sorted(base.glob("*/*.md")):
        docs.append((md.parent.name, md.name, md.stem, md.read_text(encoding="utf-8")))
    return docs


def build_chunks(docs: list[tuple[str, str, str, str]]) -> list[Chunk]:
    chunks: list[Chunk] = []
    for domain, filename, title, text in docs:
        meta = {
            "domain": domain,
            "doc_id": f"{domain}/{filename}",
            "doc_title": title,
            "source_url": "",
            "language": "mixed",
        }
        chunks.extend(chunk_markdown(text, meta))
    return chunks


def ingest(base: Path = KNOWLEDGE_DIR) -> int:
    chunks = build_chunks(load_documents(base))
    ids = [c.chunk_id for c in chunks]
    texts = [c.text for c in chunks]
    payloads = [{**c.metadata, "content": c.text} for c in chunks]

    es = ESStore()
    es.ensure_index()
    es.index_chunks(ids, texts, payloads)

    qd = QdrantStore()
    qd.ensure_collection()
    qd.upsert(ids, embed_texts(texts), payloads)

    print(f"Ingested {len(chunks)} chunks from {len(set(p['doc_id'] for p in payloads))} documents.")
    return len(chunks)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Ingest knowledge into ES + Qdrant.")
    parser.add_argument("--knowledge-dir", type=Path, default=KNOWLEDGE_DIR)
    args = parser.parse_args()
    ingest(args.knowledge_dir)
```

- [ ] **Step 4: 运行测试，确认通过**

Run: `poetry run pytest tests/test_ingest_loading.py -v`
Expected: PASS（1 passed）

- [ ] **Step 5: 提交**

```bash
git add rag/ingest.py tests/test_ingest_loading.py
git commit -m "feat(rag): ingestion pipeline (load/chunk/index)"
```

---

## Task 13: docker-compose（ES+kuromoji & Qdrant）+ Makefile

**Files:**
- Create: `docker/elasticsearch/Dockerfile`, `docker-compose.yml`, `Makefile`, `README.md`

- [ ] **Step 1: 写 `docker/elasticsearch/Dockerfile`**

```dockerfile
FROM docker.elastic.co/elasticsearch/elasticsearch:8.15.0
RUN bin/elasticsearch-plugin install --batch analysis-kuromoji
```

- [ ] **Step 2: 写 `docker-compose.yml`**

```yaml
services:
  elasticsearch:
    build: ./docker/elasticsearch
    container_name: japanlife-es
    environment:
      - discovery.type=single-node
      - xpack.security.enabled=false
      - ES_JAVA_OPTS=-Xms512m -Xmx512m
    ports:
      - "9200:9200"
    healthcheck:
      test: ["CMD-SHELL", "curl -sf http://localhost:9200/_cluster/health || exit 1"]
      interval: 10s
      timeout: 5s
      retries: 10

  qdrant:
    image: qdrant/qdrant:v1.12.1
    container_name: japanlife-qdrant
    ports:
      - "6333:6333"
    volumes:
      - qdrant_storage:/qdrant/storage

volumes:
  qdrant_storage:
```

- [ ] **Step 3: 写 `Makefile`**

```makefile
.PHONY: install up down ingest eval test

install:
	poetry install

up:
	docker compose up -d --build

down:
	docker compose down

ingest:
	poetry run python -m rag.ingest

eval:
	poetry run python -m eval.run_eval

test:
	poetry run pytest -v -m "not integration"

test-all:
	poetry run pytest -v
```

- [ ] **Step 4: 写最小 `README.md`**

```markdown
# JapanLife

Hybrid-RAG multi-agent assistant for foreigners living in Japan.

## Plan 1: Retrieval foundation

```bash
make install        # install deps
make up             # start ElasticSearch (+kuromoji) and Qdrant
make ingest         # chunk knowledge/ and index into both stores
make eval           # hybrid vs baseline retrieval metrics
make test           # unit tests (no services needed)
make test-all       # include integration tests (needs services + models)
```
```

- [ ] **Step 5: 起服务并验证健康**

```bash
make up
sleep 30
curl -sf http://localhost:9200/_cluster/health | head -c 200
curl -sf http://localhost:6333/healthz
```
Expected: ES 返回 cluster health JSON；Qdrant 返回 healthz ok。

- [ ] **Step 6: 端到端 ingest + 集成测试**

```bash
make ingest
poetry run pytest -v -m integration
```
Expected: ingest 打印已入库 chunk 数；集成测试通过。

- [ ] **Step 7: 提交**

```bash
git add docker docker-compose.yml Makefile README.md
git commit -m "chore: docker-compose (ES+kuromoji, Qdrant), Makefile, README"
```

---

## Task 14: 评测指标 `eval/metrics.py`

**Files:**
- Create: `eval/metrics.py`
- Test: `tests/test_metrics.py`

- [ ] **Step 1: 写失败测试**

`tests/test_metrics.py`:
```python
from eval.metrics import mrr, recall_at_k


def test_recall_at_k_full_hit():
    assert recall_at_k(retrieved=["d1", "d2", "d3"], relevant={"d2"}, k=3) == 1.0


def test_recall_at_k_miss_outside_k():
    assert recall_at_k(retrieved=["d1", "d2", "d3"], relevant={"d3"}, k=2) == 0.0


def test_recall_at_k_partial():
    r = recall_at_k(retrieved=["d1", "d2"], relevant={"d1", "d9"}, k=2)
    assert r == 0.5


def test_mrr_first_relevant_at_rank_2():
    assert mrr(retrieved=["x", "d1"], relevant={"d1"}) == 0.5


def test_mrr_no_hit_is_zero():
    assert mrr(retrieved=["x", "y"], relevant={"d1"}) == 0.0
```

- [ ] **Step 2: 运行测试，确认失败**

Run: `poetry run pytest tests/test_metrics.py -v`
Expected: FAIL（`ModuleNotFoundError: eval.metrics`）

- [ ] **Step 3: 实现 `eval/metrics.py`**

```python
from __future__ import annotations


def recall_at_k(retrieved: list[str], relevant: set[str], k: int) -> float:
    if not relevant:
        return 0.0
    top = set(retrieved[:k])
    return len(top & relevant) / len(relevant)


def mrr(retrieved: list[str], relevant: set[str]) -> float:
    for rank, doc_id in enumerate(retrieved, start=1):
        if doc_id in relevant:
            return 1.0 / rank
    return 0.0
```

- [ ] **Step 4: 运行测试，确认通过**

Run: `poetry run pytest tests/test_metrics.py -v`
Expected: PASS（5 passed）

- [ ] **Step 5: 提交**

```bash
git add eval/metrics.py tests/test_metrics.py
git commit -m "feat(eval): recall@k and MRR metrics"
```

---

## Task 15: 评测脚本 `eval/run_eval.py` + 数据集

**Files:**
- Create: `eval/datasets/tax.jsonl`, `eval/datasets/visa.jsonl`, `eval/datasets/ward_office.jsonl`, `eval/run_eval.py`

- [ ] **Step 1: 写评测数据集（doc 级相关性，`relevant` 用 doc_id）**

`eval/datasets/tax.jsonl`:
```json
{"question": "When is the final income tax return due?", "relevant": ["tax/01-tax-filing-overview.md"]}
{"question": "ふるさと納税の限度額はどうやって計算しますか", "relevant": ["tax/04-furusato-nozei.md"]}
{"question": "How does year-end adjustment work?", "relevant": ["tax/05-year-end-adjustment.md"]}
```

`eval/datasets/visa.jsonl`:
```json
{"question": "How many years for permanent residency?", "relevant": ["visa/01-visa-types.md"]}
{"question": "在留期間の更新はいつ申請できますか", "relevant": ["visa/02-renewal.md"]}
```

`eval/datasets/ward_office.jsonl`:
```json
{"question": "転入届はいつまでに出す必要がありますか", "relevant": ["ward_office/01-moving-in.md"]}
{"question": "What is My Number used for?", "relevant": ["ward_office/02-my-number.md"]}
```

> 注：`relevant` 用 `doc_id`（`domain/filename`）。检索结果的 `metadata["doc_id"]` 与之对齐。

- [ ] **Step 2: 实现 `eval/run_eval.py`**

```python
from __future__ import annotations

import json
from pathlib import Path

from core.config import settings
from eval.metrics import mrr, recall_at_k
from rag.embeddings import embed_query
from rag.es_store import ESStore
from rag.hybrid import fuse
from rag.qdrant_store import QdrantStore
from rag.rerank import rerank

DATASETS = Path(__file__).resolve().parent / "datasets"
K = 5


def _load_cases() -> list[dict]:
    cases = []
    for f in sorted(DATASETS.glob("*.jsonl")):
        for line in f.read_text(encoding="utf-8").splitlines():
            line = line.strip()
            if line:
                cases.append(json.loads(line))
    return cases


def _doc_ids(hits: list[tuple[str, float, dict]]) -> list[str]:
    seen, out = set(), []
    for _cid, _score, pl in hits:
        doc = pl.get("doc_id", "")
        if doc and doc not in seen:
            seen.add(doc)
            out.append(doc)
    return out


def _evaluate(name: str, run) -> tuple[float, float]:
    cases = _load_cases()
    recalls, mrrs = [], []
    for case in cases:
        relevant = set(case["relevant"])
        docs = _doc_ids(run(case["question"]))
        recalls.append(recall_at_k(docs, relevant, K))
        mrrs.append(mrr(docs, relevant))
    avg_r = sum(recalls) / len(recalls)
    avg_m = sum(mrrs) / len(mrrs)
    print(f"{name:<16} Recall@{K}={avg_r:.3f}  MRR={avg_m:.3f}")
    return avg_r, avg_m


def main() -> None:
    es = ESStore()
    qd = QdrantStore()
    top_k = settings.retrieval_top_k

    def es_only(q: str):
        return es.search(q, top_k=top_k)

    def qdrant_only(q: str):
        return qd.search(embed_query(q), top_k=top_k)

    def hybrid(q: str):
        fused = fuse(es.search(q, top_k=top_k), qd.search(embed_query(q), top_k=top_k), k=settings.rrf_k)
        return rerank(q, fused, top_n=settings.rerank_top_n)

    print("=== Retrieval evaluation ===")
    _evaluate("es_only", es_only)
    _evaluate("qdrant_only", qdrant_only)
    _evaluate("hybrid", hybrid)


if __name__ == "__main__":
    main()
```

- [ ] **Step 3: 起服务并入库（若尚未）**

```bash
make up && sleep 30 && make ingest
```
Expected: ingest 成功。

- [ ] **Step 4: 运行评测，确认混合检索不劣于基线**

Run: `make eval`
Expected: 打印三行指标，`hybrid` 的 Recall@5 ≥ 两个单路基线（这是简历可引用的对比结论）。

- [ ] **Step 5: 提交**

```bash
git add eval/run_eval.py eval/datasets
git commit -m "feat(eval): hybrid-vs-baseline retrieval evaluation"
```

---

## Self-Review 结论（已在编写时核对）

- **Spec 覆盖**：第 5 节结构（core/rag/knowledge/eval + docker/compose）→ Task 1–15 全覆盖；第 6 节混合检索（chunk/ES BM25+kuromoji/Qdrant BGE-m3/RRF/rerank/降级）→ Task 4、6–11；第 11 节 env/compose → Task 1、13；第 12 节单测+RAG eval → 各 Task 测试 + Task 14–15。
- **无占位符**：每个改代码的步骤都给了完整代码与确切命令/预期。
- **类型/命名一致**：`Chunk.chunk_id`、`payload["chunk_id"]`、`payload["content"]`、`doc_id=domain/filename`、`RetrievedChunk(text,metadata,score,citation)`、`fuse/rerank/search` 签名在 Task 4/7/8/9/10/11/12/15 间保持一致。
- **可独立交付**：完成后 `make up && make ingest && make eval && make test-all` 即可演示混合检索与指标对比。

**Plan 2 预告（不在本计划）**：领域工具 `@tool` + LangGraph supervisor/专家/handoff + FastAPI，复用本计划的 `search_knowledge_base`。
