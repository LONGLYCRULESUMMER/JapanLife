from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from app.jobs import JobRegistry
from app.knowledge_admin import KnowledgeAdminService
from app.main import app
from app.routes import (
    get_job_registry,
    get_knowledge_admin_service,
    get_reindex_fn,
)
from core.config import settings


def _payload(filename: str = "sample-guide.md") -> dict:
    return {
        "domain": "tax",
        "filename": filename,
        "metadata": {
            "doc_title": "Sample Guide",
            "source_url": "https://example.com/sample",
            "language": "en",
        },
        "body": "# Sample Guide\n\n## Overview\nBring your documents.",
    }


@pytest.fixture
def client(tmp_path: Path, monkeypatch):
    monkeypatch.setattr(settings, "deepseek_api_key", "test-key-not-used")
    service = KnowledgeAdminService(tmp_path / "knowledge")
    registry = JobRegistry()
    app.dependency_overrides[get_knowledge_admin_service] = lambda: service
    app.dependency_overrides[get_job_registry] = lambda: registry
    app.dependency_overrides[get_reindex_fn] = lambda: (lambda: 7)
    with TestClient(app) as c:
        yield c, service
    app.dependency_overrides.clear()


def test_admin_knowledge_crud_and_chunk_preview_api(client):
    c, service = client

    created = c.post("/admin/knowledge/docs", json=_payload())
    assert created.status_code == 201
    assert created.json()["doc_id"] == "tax/sample-guide.md"
    assert (service.knowledge_dir / "tax" / "sample-guide.md").exists()

    listed = c.get("/admin/knowledge/docs", params={"domain": "tax", "q": "sample"})
    assert listed.status_code == 200
    assert [doc["doc_id"] for doc in listed.json()["documents"]] == [
        "tax/sample-guide.md"
    ]

    got = c.get("/admin/knowledge/docs/tax/sample-guide.md")
    assert got.status_code == 200
    assert got.json()["metadata"]["doc_title"] == "Sample Guide"

    updated = c.put(
        "/admin/knowledge/docs/tax/sample-guide.md",
        json={
            **_payload(),
            "body": "# Sample Guide\n\n## Updated\nUpdated body.",
        },
    )
    assert updated.status_code == 200
    assert "Updated body" in updated.json()["body"]

    chunks = c.get("/admin/knowledge/docs/tax/sample-guide.md/chunks")
    assert chunks.status_code == 200
    assert chunks.json()[0]["metadata"]["doc_id"] == "tax/sample-guide.md"

    deleted = c.delete("/admin/knowledge/docs/tax/sample-guide.md")
    assert deleted.status_code == 200
    assert deleted.json()["doc_id"] == "tax/sample-guide.md"
    assert (service.knowledge_dir / ".trash" / "tax" / "sample-guide.md").exists()
    assert c.get("/admin/knowledge/docs/tax/sample-guide.md").status_code == 404


def test_validate_endpoint_returns_warning_without_hard_source_failure(client):
    c, _service = client

    response = c.post(
        "/admin/knowledge/validate",
        json={
            **_payload(),
            "metadata": {"doc_title": "Sample Guide", "source_url": "not-a-url"},
        },
    )

    assert response.status_code == 200
    body = response.json()
    assert body["valid"] is True
    assert body["errors"] == []
    assert any("source_url" in warning for warning in body["warnings"])


def test_admin_knowledge_rejects_invalid_create_payload(client):
    c, _service = client

    response = c.post(
        "/admin/knowledge/docs",
        json={**_payload(), "filename": "../secret.md"},
    )

    assert response.status_code == 400
    assert "filename" in response.json()["detail"]


def test_reindex_endpoint_runs_background_job_with_override(client):
    c, _service = client

    response = c.post("/admin/knowledge/reindex")
    assert response.status_code == 202
    job_id = response.json()["id"]

    job = c.get(f"/admin/ingest/jobs/{job_id}")
    assert job.status_code == 200
    assert job.json()["status"] == "succeeded"
    assert job.json()["chunks_indexed"] == 7
