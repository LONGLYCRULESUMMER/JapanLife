# Knowledge Admin UI Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build a Git-based knowledge-base admin API and Streamlit UI for listing, creating, editing, validating, previewing chunks, soft-deleting, and reindexing Markdown knowledge documents with stale chunk cleanup.

**Architecture:** Markdown remains the source of truth under `knowledge/<domain>/*.md`. A new backend service owns safe path resolution, front-matter rendering, validation, chunk preview, manifest tracking, and ES/Qdrant stale cleanup; FastAPI exposes `/admin/knowledge/*`; Streamlit adds a `Knowledge Admin` tab that uses those APIs.

**Tech Stack:** Python, FastAPI, Pydantic, Streamlit, pytest, existing `rag.chunking`, `rag.ingest`, `rag.es_store`, and `rag.qdrant_store`.

---

## File Structure

| File | Responsibility |
|---|---|
| `app/knowledge_admin.py` | New pure service layer for Markdown CRUD, validation, chunk preview, manifest read/write, and stale chunk diff. |
| `app/routes.py` | Add `/admin/knowledge/*` route handlers and dependency providers for the service/reindex function. |
| `app/schemas.py` | Add request/response models for knowledge admin APIs. |
| `rag/es_store.py` | Add `delete_chunks(ids)` helper used by stale cleanup. |
| `rag/qdrant_store.py` | Add `delete(ids)` helper using `point_id(chunk_id)`. |
| `streamlit_app.py` | Add `import json` bug fix and a new `Knowledge Admin` tab. |
| `tests/test_knowledge_admin.py` | Unit tests for service behavior. |
| `tests/test_knowledge_admin_api.py` | FastAPI tests for admin endpoints. |
| `tests/test_stale_cleanup.py` | Regression tests for manifest diff and ES/Qdrant stale delete calls. |

---

## Task 1: Knowledge Admin Service — safe paths, Markdown parse/render, CRUD

**Files:**
- Create: `app/knowledge_admin.py`
- Test: `tests/test_knowledge_admin.py`

- [ ] **Step 1: Write failing service tests**

Create `tests/test_knowledge_admin.py`:

```python
from pathlib import Path

import pytest

from app.knowledge_admin import (
    KnowledgeAdminService,
    KnowledgeDocInput,
    UnsafeDocIdError,
    parse_markdown_document,
    render_markdown_document,
)


def test_parse_and_render_markdown_document_roundtrip():
    text = (
        "---\n"
        "doc_title: Tax Filing\n"
        "source_url: https://example.test/tax\n"
        "language: en\n"
        "---\n\n"
        "# Tax Filing\n\n## Deadline\n\nFile in spring.\n"
    )

    doc = parse_markdown_document("tax/filing.md", text)

    assert doc.metadata["doc_title"] == "Tax Filing"
    assert doc.metadata["source_url"] == "https://example.test/tax"
    assert doc.metadata["language"] == "en"
    assert doc.body.startswith("# Tax Filing")
    assert "Deadline" in render_markdown_document(doc.metadata, doc.body)


def test_safe_doc_id_rejects_path_traversal(tmp_path: Path):
    service = KnowledgeAdminService(tmp_path)

    with pytest.raises(UnsafeDocIdError):
        service.path_for_doc_id("../secrets.md")


def test_create_list_get_update_and_soft_delete(tmp_path: Path):
    service = KnowledgeAdminService(tmp_path)
    payload = KnowledgeDocInput(
        domain="tax",
        filename="new-guide.md",
        doc_title="New Guide",
        source_url="https://example.test/source",
        language="en",
        body="# New Guide\n\n## Overview\n\nBody text.",
    )

    created = service.create_document(payload)
    assert created.doc_id == "tax/new-guide.md"
    assert created.needs_reindex is True

    docs = service.list_documents(domain="tax")
    assert [d.doc_id for d in docs] == ["tax/new-guide.md"]

    got = service.get_document("tax/new-guide.md")
    assert got.doc_title == "New Guide"

    updated = service.update_document(
        "tax/new-guide.md",
        payload.model_copy(update={"doc_title": "Updated Guide"}),
    )
    assert updated.doc_title == "Updated Guide"

    deleted = service.soft_delete_document("tax/new-guide.md")
    assert deleted.doc_id == "tax/new-guide.md"
    assert not (tmp_path / "tax" / "new-guide.md").exists()
    assert (tmp_path / ".trash" / "tax" / "new-guide.md").exists()
    assert service.list_documents(domain="tax") == []
```

- [ ] **Step 2: Run tests and verify they fail**

Run:

```bash
poetry run pytest -q tests/test_knowledge_admin.py
```

Expected: import failure for `app.knowledge_admin`.

- [ ] **Step 3: Implement service models and CRUD**

Create `app/knowledge_admin.py`:

```python
from __future__ import annotations

import re
import shutil
from dataclasses import dataclass
from pathlib import Path

from pydantic import BaseModel

from rag.chunking import split_front_matter

ALLOWED_DOMAINS = {"tax", "visa", "ward_office"}
FILENAME_RE = re.compile(r"^[a-z0-9][a-z0-9-]*(?:\.ja)?\.md$")
REQUIRED_FRONT_MATTER = ("doc_title", "source_url", "language")
VALID_LANGUAGES = {"en", "ja", "mixed"}


class KnowledgeAdminError(ValueError):
    pass


class UnsafeDocIdError(KnowledgeAdminError):
    pass


class ValidationError(KnowledgeAdminError):
    pass


class KnowledgeDocInput(BaseModel):
    domain: str
    filename: str
    doc_title: str
    source_url: str
    language: str
    body: str


class KnowledgeDoc(BaseModel):
    doc_id: str
    domain: str
    filename: str
    doc_title: str
    source_url: str
    language: str
    body: str = ""
    needs_reindex: bool = False


@dataclass(frozen=True)
class ParsedMarkdown:
    doc_id: str
    metadata: dict[str, str]
    body: str


def parse_markdown_document(doc_id: str, text: str) -> ParsedMarkdown:
    metadata, body = split_front_matter(text)
    return ParsedMarkdown(doc_id=doc_id, metadata={str(k): str(v) for k, v in metadata.items()}, body=body)


def render_markdown_document(metadata: dict[str, str], body: str) -> str:
    ordered = []
    for key in ("doc_title", "source_url", "language", "last_updated"):
        if key in metadata:
            ordered.append((key, metadata[key]))
    for key in sorted(k for k in metadata if k not in {k for k, _ in ordered}):
        ordered.append((key, metadata[key]))
    front = "\n".join(f"{key}: {value}" for key, value in ordered)
    return f"---\n{front}\n---\n\n{body.strip()}\n"


class KnowledgeAdminService:
    def __init__(self, knowledge_dir: Path):
        self.knowledge_dir = knowledge_dir.resolve()

    def _validate_domain_filename(self, domain: str, filename: str) -> None:
        if domain not in ALLOWED_DOMAINS:
            raise ValidationError(f"Unsupported domain: {domain}")
        if not FILENAME_RE.fullmatch(filename):
            raise ValidationError("Filename must be lowercase kebab-case ending in .md or .ja.md")

    def path_for_doc_id(self, doc_id: str) -> Path:
        parts = doc_id.split("/", 1)
        if len(parts) != 2:
            raise UnsafeDocIdError("doc_id must be domain/filename")
        domain, filename = parts
        self._validate_domain_filename(domain, filename)
        path = (self.knowledge_dir / domain / filename).resolve()
        if self.knowledge_dir not in path.parents:
            raise UnsafeDocIdError("doc_id escapes knowledge directory")
        return path

    def _doc_from_path(self, path: Path, include_body: bool = False) -> KnowledgeDoc:
        domain = path.parent.name
        doc_id = f"{domain}/{path.name}"
        parsed = parse_markdown_document(doc_id, path.read_text(encoding="utf-8"))
        return KnowledgeDoc(
            doc_id=doc_id,
            domain=domain,
            filename=path.name,
            doc_title=parsed.metadata.get("doc_title") or path.stem,
            source_url=parsed.metadata.get("source_url", ""),
            language=parsed.metadata.get("language", "mixed"),
            body=parsed.body if include_body else "",
        )

    def list_documents(self, domain: str | None = None, q: str = "") -> list[KnowledgeDoc]:
        domains = [domain] if domain else sorted(ALLOWED_DOMAINS)
        docs: list[KnowledgeDoc] = []
        for dom in domains:
            if dom not in ALLOWED_DOMAINS:
                raise ValidationError(f"Unsupported domain: {dom}")
            for path in sorted((self.knowledge_dir / dom).glob("*.md")):
                doc = self._doc_from_path(path)
                haystack = f"{doc.doc_id} {doc.doc_title} {doc.source_url}".lower()
                if q.lower() in haystack:
                    docs.append(doc)
        return docs

    def get_document(self, doc_id: str) -> KnowledgeDoc:
        path = self.path_for_doc_id(doc_id)
        if not path.exists():
            raise FileNotFoundError(doc_id)
        return self._doc_from_path(path, include_body=True)

    def _metadata_from_input(self, payload: KnowledgeDocInput) -> dict[str, str]:
        return {
            "doc_title": payload.doc_title.strip(),
            "source_url": payload.source_url.strip(),
            "language": payload.language.strip(),
        }

    def _validate_payload(self, payload: KnowledgeDocInput) -> None:
        self._validate_domain_filename(payload.domain, payload.filename)
        metadata = self._metadata_from_input(payload)
        for key in REQUIRED_FRONT_MATTER:
            if not metadata.get(key):
                raise ValidationError(f"Missing {key}")
        if metadata["language"] not in VALID_LANGUAGES:
            raise ValidationError("language must be en, ja, or mixed")
        if "#" not in payload.body:
            raise ValidationError("Markdown body must contain at least one heading")

    def create_document(self, payload: KnowledgeDocInput) -> KnowledgeDoc:
        self._validate_payload(payload)
        path = self.path_for_doc_id(f"{payload.domain}/{payload.filename}")
        if path.exists():
            raise FileExistsError(path)
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(render_markdown_document(self._metadata_from_input(payload), payload.body), encoding="utf-8")
        return self.get_document(f"{payload.domain}/{payload.filename}").model_copy(update={"needs_reindex": True})

    def update_document(self, doc_id: str, payload: KnowledgeDocInput) -> KnowledgeDoc:
        self._validate_payload(payload)
        path = self.path_for_doc_id(doc_id)
        if not path.exists():
            raise FileNotFoundError(doc_id)
        if f"{payload.domain}/{payload.filename}" != doc_id:
            raise ValidationError("Cannot change doc_id in update")
        path.write_text(render_markdown_document(self._metadata_from_input(payload), payload.body), encoding="utf-8")
        return self.get_document(doc_id).model_copy(update={"needs_reindex": True})

    def soft_delete_document(self, doc_id: str) -> KnowledgeDoc:
        doc = self.get_document(doc_id)
        source = self.path_for_doc_id(doc_id)
        trash = (self.knowledge_dir / ".trash" / doc.domain / doc.filename).resolve()
        trash.parent.mkdir(parents=True, exist_ok=True)
        shutil.move(str(source), str(trash))
        return doc.model_copy(update={"needs_reindex": True})
```

- [ ] **Step 4: Run service tests**

Run:

```bash
poetry run pytest -q tests/test_knowledge_admin.py
```

Expected: all tests pass.

- [ ] **Step 5: Commit**

```bash
git add app/knowledge_admin.py tests/test_knowledge_admin.py
git commit -m "feat(admin): add knowledge Markdown admin service" -m "Co-authored-by: Copilot <223556219+Copilot@users.noreply.github.com>"
```

---

## Task 2: Validation and Chunk Preview

**Files:**
- Modify: `app/knowledge_admin.py`
- Modify: `tests/test_knowledge_admin.py`

- [ ] **Step 1: Add failing tests for validation and chunk preview**

Append to `tests/test_knowledge_admin.py`:

```python
def test_validate_document_reports_errors_and_warnings(tmp_path: Path):
    service = KnowledgeAdminService(tmp_path)
    payload = KnowledgeDocInput(
        domain="tax",
        filename="bad.md",
        doc_title="",
        source_url="not-a-url",
        language="xx",
        body="plain body",
    )

    result = service.validate_document(payload, check_source=False)

    assert result["valid"] is False
    assert "Missing doc_title" in result["errors"]
    assert "language must be en, ja, or mixed" in result["errors"]
    assert "Markdown body must contain at least one heading" in result["errors"]
    assert "source_url should start with http:// or https://" in result["warnings"]


def test_preview_chunks_returns_chunk_metadata(tmp_path: Path):
    service = KnowledgeAdminService(tmp_path)
    service.create_document(
        KnowledgeDocInput(
            domain="tax",
            filename="chunk-me.md",
            doc_title="Chunk Me",
            source_url="https://example.test/chunk",
            language="en",
            body="# Chunk Me\n\n## A\n\nhello world",
        )
    )

    chunks = service.preview_chunks("tax/chunk-me.md")

    assert len(chunks) == 1
    assert chunks[0]["metadata"]["doc_id"] == "tax/chunk-me.md"
    assert chunks[0]["metadata"]["section_path"] == "A"
    assert chunks[0]["text"] == "hello world"
```

- [ ] **Step 2: Run tests and verify they fail**

Run:

```bash
poetry run pytest -q tests/test_knowledge_admin.py
```

Expected: failures for missing `validate_document` and `preview_chunks`.

- [ ] **Step 3: Implement validation and chunk preview**

Modify imports in `app/knowledge_admin.py`:

```python
import httpx
from rag.chunking import chunk_markdown, split_front_matter
```

Add methods to `KnowledgeAdminService`:

```python
    def validate_document(self, payload: KnowledgeDocInput, check_source: bool = True) -> dict:
        errors: list[str] = []
        warnings: list[str] = []
        try:
            self._validate_domain_filename(payload.domain, payload.filename)
        except ValidationError as exc:
            errors.append(str(exc))

        metadata = self._metadata_from_input(payload)
        for key in REQUIRED_FRONT_MATTER:
            if not metadata.get(key):
                errors.append(f"Missing {key}")
        if metadata.get("language") and metadata["language"] not in VALID_LANGUAGES:
            errors.append("language must be en, ja, or mixed")
        if "#" not in payload.body:
            errors.append("Markdown body must contain at least one heading")
        if metadata.get("source_url") and not metadata["source_url"].startswith(("http://", "https://")):
            warnings.append("source_url should start with http:// or https://")
        elif check_source and metadata.get("source_url"):
            try:
                response = httpx.get(metadata["source_url"], follow_redirects=True, timeout=10)
                if response.status_code >= 400:
                    warnings.append(f"source_url returned HTTP {response.status_code}")
            except Exception as exc:
                warnings.append(f"source_url check failed: {exc}")
        return {"valid": not errors, "errors": errors, "warnings": warnings}

    def preview_chunks(self, doc_id: str) -> list[dict]:
        doc = self.get_document(doc_id)
        metadata = {
            "domain": doc.domain,
            "doc_id": doc.doc_id,
            "doc_title": doc.doc_title,
            "source_url": doc.source_url,
            "language": doc.language,
        }
        return [
            {
                "chunk_id": chunk.chunk_id,
                "text": chunk.text,
                "metadata": chunk.metadata,
            }
            for chunk in chunk_markdown(doc.body, metadata)
        ]
```

- [ ] **Step 4: Run service tests**

Run:

```bash
poetry run pytest -q tests/test_knowledge_admin.py
```

Expected: all tests pass.

- [ ] **Step 5: Commit**

```bash
git add app/knowledge_admin.py tests/test_knowledge_admin.py
git commit -m "feat(admin): validate knowledge docs and preview chunks" -m "Co-authored-by: Copilot <223556219+Copilot@users.noreply.github.com>"
```

---

## Task 3: Manifest and Stale Chunk Cleanup

**Files:**
- Modify: `app/knowledge_admin.py`
- Modify: `rag/es_store.py`
- Modify: `rag/qdrant_store.py`
- Create: `tests/test_stale_cleanup.py`

- [ ] **Step 1: Add failing stale cleanup tests**

Create `tests/test_stale_cleanup.py`:

```python
from pathlib import Path

from app.knowledge_admin import KnowledgeAdminService, KnowledgeDocInput


class FakeES:
    def __init__(self):
        self.deleted = []

    def delete_chunks(self, ids):
        self.deleted.extend(ids)


class FakeQdrant:
    def __init__(self):
        self.deleted = []

    def delete(self, ids):
        self.deleted.extend(ids)


def test_manifest_records_current_chunks(tmp_path: Path):
    service = KnowledgeAdminService(tmp_path)
    service.create_document(
        KnowledgeDocInput(
            domain="tax",
            filename="guide.md",
            doc_title="Guide",
            source_url="https://example.test/guide",
            language="en",
            body="# Guide\n\n## One\n\nBody",
        )
    )

    chunks = service.preview_chunks("tax/guide.md")
    service.write_manifest_from_chunks(chunks)

    manifest = service.read_manifest()
    assert manifest["documents"]["tax/guide.md"]["chunk_ids"] == [chunks[0]["chunk_id"]]


def test_delete_stale_chunks_calls_both_stores(tmp_path: Path):
    service = KnowledgeAdminService(tmp_path)
    service.write_manifest(
        {
            "documents": {
                "tax/old.md": {"status": "active", "chunk_ids": ["old1", "old2"], "updated_at": "now"}
            },
            "deleted_documents": {},
        }
    )
    es = FakeES()
    qd = FakeQdrant()

    stale = service.delete_stale_chunks(current_chunk_ids={"old2"}, es=es, qdrant=qd)

    assert stale == ["old1"]
    assert es.deleted == ["old1"]
    assert qd.deleted == ["old1"]
```

- [ ] **Step 2: Run tests and verify they fail**

Run:

```bash
poetry run pytest -q tests/test_stale_cleanup.py
```

Expected: failures for missing manifest/stale cleanup methods.

- [ ] **Step 3: Add ES/Qdrant delete helpers**

Add to `rag/es_store.py` inside `ESStore`:

```python
    def delete_chunks(self, ids: list[str]) -> None:
        if not ids:
            return
        actions = [{"_op_type": "delete", "_index": self.index, "_id": cid} for cid in ids]
        bulk(self.client, actions, ignore_status=(404,))
        self.client.indices.refresh(index=self.index)
```

Add imports in `rag/qdrant_store.py`:

```python
from qdrant_client.models import PointIdsList
```

Add to `QdrantStore`:

```python
    def delete(self, ids: list[str]) -> None:
        if not ids:
            return
        self.client.delete(
            collection_name=self.collection,
            points_selector=PointIdsList(points=[point_id(cid) for cid in ids]),
        )
```

- [ ] **Step 4: Add manifest methods**

Add imports to `app/knowledge_admin.py`:

```python
import json
from datetime import datetime, timezone
```

Add methods to `KnowledgeAdminService`:

```python
    @property
    def manifest_path(self) -> Path:
        return self.knowledge_dir / ".manifest.json"

    def read_manifest(self) -> dict:
        if not self.manifest_path.exists():
            return {"documents": {}, "deleted_documents": {}}
        return json.loads(self.manifest_path.read_text(encoding="utf-8"))

    def write_manifest(self, manifest: dict) -> None:
        self.manifest_path.write_text(json.dumps(manifest, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

    def write_manifest_from_chunks(self, chunks: list[dict]) -> None:
        documents: dict[str, dict] = {}
        now = datetime.now(timezone.utc).isoformat()
        for chunk in chunks:
            doc_id = chunk["metadata"]["doc_id"]
            documents.setdefault(doc_id, {"status": "active", "chunk_ids": [], "updated_at": now})
            documents[doc_id]["chunk_ids"].append(chunk["chunk_id"])
        self.write_manifest({"documents": documents, "deleted_documents": self.read_manifest().get("deleted_documents", {})})

    def all_active_chunks(self) -> list[dict]:
        chunks: list[dict] = []
        for doc in self.list_documents():
            chunks.extend(self.preview_chunks(doc.doc_id))
        return chunks

    def delete_stale_chunks(self, current_chunk_ids: set[str], es, qdrant) -> list[str]:
        manifest = self.read_manifest()
        previous = {
            chunk_id
            for doc in manifest.get("documents", {}).values()
            for chunk_id in doc.get("chunk_ids", [])
        }
        stale = sorted(previous - current_chunk_ids)
        if stale:
            es.delete_chunks(stale)
            qdrant.delete(stale)
        return stale
```

- [ ] **Step 5: Run stale cleanup tests**

Run:

```bash
poetry run pytest -q tests/test_stale_cleanup.py tests/test_knowledge_admin.py
```

Expected: all tests pass.

- [ ] **Step 6: Commit**

```bash
git add app/knowledge_admin.py rag/es_store.py rag/qdrant_store.py tests/test_stale_cleanup.py
git commit -m "feat(admin): track manifest and delete stale chunks" -m "Co-authored-by: Copilot <223556219+Copilot@users.noreply.github.com>"
```

---

## Task 4: FastAPI Knowledge Admin Routes

**Files:**
- Modify: `app/schemas.py`
- Modify: `app/routes.py`
- Create: `tests/test_knowledge_admin_api.py`

- [ ] **Step 1: Add failing API tests**

Create `tests/test_knowledge_admin_api.py`:

```python
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from app.jobs import JobRegistry
from app.main import app
from app.routes import get_job_registry, get_knowledge_admin_service, get_reindex_fn
from app.knowledge_admin import KnowledgeAdminService


@pytest.fixture
def client(tmp_path: Path):
    service = KnowledgeAdminService(tmp_path)
    registry = JobRegistry()
    app.dependency_overrides[get_knowledge_admin_service] = lambda: service
    app.dependency_overrides[get_job_registry] = lambda: registry
    app.dependency_overrides[get_reindex_fn] = lambda: (lambda: 0)
    with TestClient(app) as c:
        yield c
    app.dependency_overrides.clear()


def test_create_list_get_update_delete_doc(client):
    payload = {
        "domain": "tax",
        "filename": "api-guide.md",
        "doc_title": "API Guide",
        "source_url": "https://example.test/api",
        "language": "en",
        "body": "# API Guide\n\n## Overview\n\nBody",
    }
    created = client.post("/admin/knowledge/docs", json=payload)
    assert created.status_code == 201
    assert created.json()["doc_id"] == "tax/api-guide.md"

    listed = client.get("/admin/knowledge/docs?domain=tax").json()["documents"]
    assert listed[0]["doc_id"] == "tax/api-guide.md"

    got = client.get("/admin/knowledge/docs/tax/api-guide.md").json()
    assert got["body"].startswith("# API Guide")

    payload["doc_title"] = "Updated API Guide"
    updated = client.put("/admin/knowledge/docs/tax/api-guide.md", json=payload)
    assert updated.status_code == 200
    assert updated.json()["doc_title"] == "Updated API Guide"

    deleted = client.delete("/admin/knowledge/docs/tax/api-guide.md")
    assert deleted.status_code == 200
    assert deleted.json()["needs_reindex"] is True


def test_preview_chunks_and_validate(client):
    payload = {
        "domain": "tax",
        "filename": "chunk-api.md",
        "doc_title": "Chunk API",
        "source_url": "https://example.test/chunk",
        "language": "en",
        "body": "# Chunk API\n\n## One\n\nText",
    }
    assert client.post("/admin/knowledge/docs", json=payload).status_code == 201

    validation = client.post("/admin/knowledge/validate", json=payload).json()
    assert validation["valid"] is True

    chunks = client.get("/admin/knowledge/docs/tax/chunk-api.md/chunks").json()["chunks"]
    assert len(chunks) == 1


def test_reindex_starts_job(client):
    response = client.post("/admin/knowledge/reindex")
    assert response.status_code == 202
    assert response.json()["status"] in ("pending", "running", "succeeded")
```

- [ ] **Step 2: Run API tests and verify they fail**

Run:

```bash
poetry run pytest -q tests/test_knowledge_admin_api.py
```

Expected: import failure for missing route dependencies.

- [ ] **Step 3: Add schemas**

Append to `app/schemas.py`:

```python
class KnowledgeDocRequest(BaseModel):
    domain: str
    filename: str
    doc_title: str
    source_url: str
    language: str
    body: str


class KnowledgeDocResponse(BaseModel):
    doc_id: str
    domain: str
    filename: str
    doc_title: str
    source_url: str
    language: str
    body: str = ""
    needs_reindex: bool = False


class KnowledgeDocListResponse(BaseModel):
    documents: list[KnowledgeDocResponse]


class KnowledgeValidationResponse(BaseModel):
    valid: bool
    errors: list[str]
    warnings: list[str]


class ChunkPreviewResponse(BaseModel):
    chunks: list[dict]
```

- [ ] **Step 4: Add route dependencies and endpoints**

Modify imports in `app/routes.py`:

```python
from pathlib import Path

from app.schemas import (
    ChatRequest,
    ChatResponse,
    ChunkPreviewResponse,
    KnowledgeDocListResponse,
    KnowledgeDocRequest,
    KnowledgeDocResponse,
    KnowledgeValidationResponse,
)
from app.knowledge_admin import KnowledgeAdminService, KnowledgeDocInput, KnowledgeAdminError, ValidationError
```

Add dependency providers near existing providers:

```python
def get_knowledge_admin_service():
    return KnowledgeAdminService(Path(__file__).resolve().parent.parent / "knowledge")


def get_reindex_fn(service=Depends(get_knowledge_admin_service)):
    def _run() -> int:
        from rag.ingest import ingest
        from rag.es_store import ESStore
        from rag.qdrant_store import QdrantStore

        count = ingest(service.knowledge_dir)
        chunks = service.all_active_chunks()
        current = {chunk["chunk_id"] for chunk in chunks}
        service.delete_stale_chunks(current, ESStore(), QdrantStore())
        service.write_manifest_from_chunks(chunks)
        return count

    return _run
```

Add helper:

```python
def _to_doc_input(req: KnowledgeDocRequest) -> KnowledgeDocInput:
    return KnowledgeDocInput(**req.model_dump())
```

Add endpoints:

```python
@router.get("/admin/knowledge/docs", response_model=KnowledgeDocListResponse)
def list_knowledge_docs(domain: str = "", q: str = "", service=Depends(get_knowledge_admin_service)):
    try:
        return {"documents": service.list_documents(domain=domain or None, q=q)}
    except KnowledgeAdminError as exc:
        raise HTTPException(status_code=400, detail=str(exc))


@router.get("/admin/knowledge/docs/{domain}/{filename}", response_model=KnowledgeDocResponse)
def get_knowledge_doc(domain: str, filename: str, service=Depends(get_knowledge_admin_service)):
    try:
        return service.get_document(f"{domain}/{filename}")
    except FileNotFoundError:
        raise HTTPException(status_code=404, detail="Knowledge document not found.")
    except KnowledgeAdminError as exc:
        raise HTTPException(status_code=400, detail=str(exc))


@router.post("/admin/knowledge/docs", response_model=KnowledgeDocResponse, status_code=201)
def create_knowledge_doc(req: KnowledgeDocRequest, service=Depends(get_knowledge_admin_service)):
    try:
        return service.create_document(_to_doc_input(req))
    except FileExistsError:
        raise HTTPException(status_code=409, detail="Knowledge document already exists.")
    except KnowledgeAdminError as exc:
        raise HTTPException(status_code=400, detail=str(exc))


@router.put("/admin/knowledge/docs/{domain}/{filename}", response_model=KnowledgeDocResponse)
def update_knowledge_doc(domain: str, filename: str, req: KnowledgeDocRequest, service=Depends(get_knowledge_admin_service)):
    try:
        return service.update_document(f"{domain}/{filename}", _to_doc_input(req))
    except FileNotFoundError:
        raise HTTPException(status_code=404, detail="Knowledge document not found.")
    except KnowledgeAdminError as exc:
        raise HTTPException(status_code=400, detail=str(exc))


@router.delete("/admin/knowledge/docs/{domain}/{filename}", response_model=KnowledgeDocResponse)
def delete_knowledge_doc(domain: str, filename: str, service=Depends(get_knowledge_admin_service)):
    try:
        return service.soft_delete_document(f"{domain}/{filename}")
    except FileNotFoundError:
        raise HTTPException(status_code=404, detail="Knowledge document not found.")
    except KnowledgeAdminError as exc:
        raise HTTPException(status_code=400, detail=str(exc))


@router.post("/admin/knowledge/validate", response_model=KnowledgeValidationResponse)
def validate_knowledge_doc(req: KnowledgeDocRequest, service=Depends(get_knowledge_admin_service)):
    return service.validate_document(_to_doc_input(req))


@router.get("/admin/knowledge/docs/{domain}/{filename}/chunks", response_model=ChunkPreviewResponse)
def preview_knowledge_chunks(domain: str, filename: str, service=Depends(get_knowledge_admin_service)):
    try:
        return {"chunks": service.preview_chunks(f"{domain}/{filename}")}
    except FileNotFoundError:
        raise HTTPException(status_code=404, detail="Knowledge document not found.")
    except KnowledgeAdminError as exc:
        raise HTTPException(status_code=400, detail=str(exc))


@router.post("/admin/knowledge/reindex", status_code=202)
def trigger_knowledge_reindex(
    background_tasks: BackgroundTasks,
    registry=Depends(get_job_registry),
    reindex_fn=Depends(get_reindex_fn),
):
    job = registry.create()
    background_tasks.add_task(registry.run, job.id, reindex_fn)
    return job.to_dict()
```

- [ ] **Step 5: Run API tests**

Run:

```bash
poetry run pytest -q tests/test_knowledge_admin_api.py tests/test_knowledge_admin.py tests/test_stale_cleanup.py
```

Expected: all tests pass.

- [ ] **Step 6: Commit**

```bash
git add app/routes.py app/schemas.py tests/test_knowledge_admin_api.py
git commit -m "feat(api): expose knowledge admin endpoints" -m "Co-authored-by: Copilot <223556219+Copilot@users.noreply.github.com>"
```

---

## Task 5: Streamlit Knowledge Admin Tab

**Files:**
- Modify: `streamlit_app.py`

- [ ] **Step 1: Add API helpers and import**

Modify imports at the top:

```python
import json
import os
```

Add helper functions after conversation helpers:

```python
def list_knowledge_docs(domain: str = "", q: str = "") -> list[dict]:
    params = {}
    if domain:
        params["domain"] = domain
    if q:
        params["q"] = q
    return httpx.get(f"{API_URL}/admin/knowledge/docs", params=params, timeout=30).json().get("documents", [])


def get_knowledge_doc(doc_id: str) -> dict:
    return httpx.get(f"{API_URL}/admin/knowledge/docs/{doc_id}", timeout=30).json()


def save_knowledge_doc(payload: dict, existing_doc_id: str | None = None) -> dict:
    if existing_doc_id:
        r = httpx.put(f"{API_URL}/admin/knowledge/docs/{existing_doc_id}", json=payload, timeout=30)
    else:
        r = httpx.post(f"{API_URL}/admin/knowledge/docs", json=payload, timeout=30)
    r.raise_for_status()
    return r.json()


def delete_knowledge_doc_api(doc_id: str) -> dict:
    r = httpx.delete(f"{API_URL}/admin/knowledge/docs/{doc_id}", timeout=30)
    r.raise_for_status()
    return r.json()


def validate_knowledge_doc_api(payload: dict) -> dict:
    r = httpx.post(f"{API_URL}/admin/knowledge/validate", json=payload, timeout=30)
    r.raise_for_status()
    return r.json()


def preview_knowledge_chunks_api(doc_id: str) -> list[dict]:
    r = httpx.get(f"{API_URL}/admin/knowledge/docs/{doc_id}/chunks", timeout=30)
    r.raise_for_status()
    return r.json().get("chunks", [])


def trigger_knowledge_reindex_api() -> dict:
    r = httpx.post(f"{API_URL}/admin/knowledge/reindex", timeout=30)
    r.raise_for_status()
    return r.json()
```

- [ ] **Step 2: Add tab name**

Change:

```python
overview_tab, chat_tab, retrieval_tab = st.tabs(
    ["📐 Overview & Architecture", "💬 Chat", "🔎 Retrieval inspector"]
)
```

to:

```python
overview_tab, chat_tab, retrieval_tab, admin_tab = st.tabs(
    ["📐 Overview & Architecture", "💬 Chat", "🔎 Retrieval inspector", "🗂 Knowledge Admin"]
)
```

- [ ] **Step 3: Add admin tab UI**

Append after the retrieval tab block:

```python
with admin_tab:
    st.header("🗂 Knowledge Admin")
    st.caption("Git-based Markdown admin for `knowledge/<domain>/*.md`.")
    if health is None:
        st.warning("Backend is unreachable — start it with `make up` / `make serve`.")
    else:
        filters = st.columns([2, 3, 1])
        admin_domain = filters[0].selectbox("Admin domain", ["tax", "visa", "ward_office"], key="admin_domain")
        admin_query = filters[1].text_input("Search documents", key="admin_query")
        if filters[2].button("Refresh", use_container_width=True):
            st.session_state.pop("knowledge_docs_cache", None)

        try:
            docs = list_knowledge_docs(admin_domain, admin_query)
        except Exception as exc:
            docs = []
            st.error(f"Could not load knowledge docs: {exc}")

        left, right = st.columns([2, 3])
        with left:
            st.subheader("Documents")
            selected_doc = st.session_state.get("selected_knowledge_doc")
            for doc in docs:
                label = f"{doc['doc_id']} · {doc.get('language', 'mixed')}"
                if st.button(label, key=f"select_doc_{doc['doc_id']}", use_container_width=True):
                    st.session_state.selected_knowledge_doc = doc["doc_id"]
                    st.rerun()
            if st.button("➕ New document", use_container_width=True):
                st.session_state.selected_knowledge_doc = None
                st.rerun()

        with right:
            st.subheader("Editor")
            selected_doc = st.session_state.get("selected_knowledge_doc")
            existing = None
            if selected_doc:
                try:
                    existing = get_knowledge_doc(selected_doc)
                except Exception as exc:
                    st.error(f"Could not load document: {exc}")

            default_domain = existing.get("domain") if existing else admin_domain
            default_filename = existing.get("filename") if existing else "new-guide.md"
            default_title = existing.get("doc_title") if existing else ""
            default_source = existing.get("source_url") if existing else "https://example.com/source"
            default_language = existing.get("language") if existing else "en"
            default_body = existing.get("body") if existing else "# New Guide\n\n## Overview\n\nWrite content here."

            domain_value = st.selectbox("Domain", ["tax", "visa", "ward_office"], index=["tax", "visa", "ward_office"].index(default_domain))
            filename_value = st.text_input("Filename", value=default_filename)
            title_value = st.text_input("doc_title", value=default_title)
            source_value = st.text_input("source_url", value=default_source)
            language_value = st.selectbox("language", ["en", "ja", "mixed"], index=["en", "ja", "mixed"].index(default_language if default_language in ["en", "ja", "mixed"] else "mixed"))
            body_value = st.text_area("Markdown body", value=default_body, height=320)

            payload = {
                "domain": domain_value,
                "filename": filename_value,
                "doc_title": title_value,
                "source_url": source_value,
                "language": language_value,
                "body": body_value,
            }

            actions = st.columns(5)
            if actions[0].button("Validate"):
                try:
                    result = validate_knowledge_doc_api(payload)
                    if result["valid"]:
                        st.success("Valid front-matter and Markdown shape.")
                    else:
                        st.error("Validation failed.")
                    for err in result.get("errors", []):
                        st.error(err)
                    for warn in result.get("warnings", []):
                        st.warning(warn)
                except Exception as exc:
                    st.error(f"Validation failed: {exc}")

            if actions[1].button("Save"):
                try:
                    saved = save_knowledge_doc(payload, selected_doc)
                    st.session_state.selected_knowledge_doc = saved["doc_id"]
                    st.success(f"Saved {saved['doc_id']}. Reindex is required.")
                except Exception as exc:
                    st.error(f"Save failed: {exc}")

            if actions[2].button("Preview chunks") and selected_doc:
                try:
                    chunks = preview_knowledge_chunks_api(selected_doc)
                    st.info(f"{len(chunks)} chunk(s)")
                    for chunk in chunks[:10]:
                        st.markdown(f"**{chunk['chunk_id']}** · {chunk['metadata'].get('section_path', '')}")
                        st.caption(chunk["text"][:500])
                except Exception as exc:
                    st.error(f"Chunk preview failed: {exc}")

            if actions[3].button("Soft delete", disabled=not bool(selected_doc)):
                try:
                    deleted = delete_knowledge_doc_api(selected_doc)
                    st.session_state.selected_knowledge_doc = None
                    st.warning(f"Soft-deleted {deleted['doc_id']}. Reindex is required.")
                except Exception as exc:
                    st.error(f"Delete failed: {exc}")

            if actions[4].button("Reindex"):
                try:
                    job = trigger_knowledge_reindex_api()
                    st.success(f"Started reindex job {job['id']} ({job['status']}).")
                except Exception as exc:
                    st.error(f"Reindex failed: {exc}")
```

- [ ] **Step 4: Run Streamlit import smoke**

Run:

```bash
poetry run python -m py_compile streamlit_app.py
```

Expected: exits 0.

- [ ] **Step 5: Commit**

```bash
git add streamlit_app.py
git commit -m "feat(ui): add Streamlit knowledge admin tab" -m "Co-authored-by: Copilot <223556219+Copilot@users.noreply.github.com>"
```

---

## Task 6: Documentation and Final Verification

**Files:**
- Modify: `README.md`
- Modify: `docs/backend-engineering.md`

- [ ] **Step 1: Update documentation**

In `README.md`, add Knowledge Admin to API/highlights/project-structure sections. Include these endpoints:

```text
GET /admin/knowledge/docs
POST /admin/knowledge/docs
PUT /admin/knowledge/docs/{doc_id}
DELETE /admin/knowledge/docs/{doc_id}
GET /admin/knowledge/docs/{doc_id}/chunks
POST /admin/knowledge/reindex
```

In `docs/backend-engineering.md`, add a short section:

```markdown
## Knowledge Admin

The admin layer keeps Markdown as the source of truth while adding safe CRUD, validation,
chunk preview, and manifest-backed stale chunk cleanup. Deletes are soft by default: files move
to `knowledge/.trash/`, and `/admin/knowledge/reindex` removes stale ES/Qdrant chunks after the
next successful index pass.
```

- [ ] **Step 2: Run full verification**

Run:

```bash
poetry run pytest -q tests/test_knowledge_admin.py tests/test_stale_cleanup.py tests/test_knowledge_admin_api.py
make test
poetry run python -m py_compile streamlit_app.py
```

Expected: all tests pass and py_compile exits 0.

- [ ] **Step 3: Commit**

```bash
git add README.md docs/backend-engineering.md
git commit -m "docs: document knowledge admin workflow" -m "Co-authored-by: Copilot <223556219+Copilot@users.noreply.github.com>"
```

---

## Self-Review

**Spec coverage:** Tasks cover Git-based Markdown CRUD, validation, source URL warning, chunk preview, soft delete, manifest-backed stale cleanup, admin API, Streamlit UI, docs, and tests.

**Placeholder scan:** No TBD/TODO/fill-in placeholders remain. Each task names exact files, commands, and expected outcomes.

**Type consistency:** Request/response schemas use `domain`, `filename`, `doc_title`, `source_url`, `language`, `body`, `doc_id`, and `needs_reindex` consistently across service, API, and Streamlit UI.

