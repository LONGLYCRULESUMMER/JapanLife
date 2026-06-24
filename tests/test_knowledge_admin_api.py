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

ADMIN_HEADERS = {"x-admin-token": "test-admin"}


def _payload(filename: str = "sample-guide.md") -> dict:
    return {
        "domain": "tax",
        "filename": filename,
        "doc_title": "Sample Guide",
        "source_url": "https://example.com/sample",
        "language": "en",
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
    monkeypatch.setattr(settings, "admin_api_key", "test-admin")
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

    created = c.post("/admin/knowledge/docs", json=_payload(), headers=ADMIN_HEADERS)
    assert created.status_code == 201
    assert created.json()["doc_id"] == "tax/sample-guide.md"
    assert (service.knowledge_dir / "tax" / "sample-guide.md").exists()

    listed = c.get("/admin/knowledge/docs", params={"domain": "tax", "q": "sample"}, headers=ADMIN_HEADERS)
    assert listed.status_code == 200
    assert [doc["doc_id"] for doc in listed.json()["documents"]] == [
        "tax/sample-guide.md"
    ]

    got = c.get("/admin/knowledge/docs/tax/sample-guide.md", headers=ADMIN_HEADERS)
    assert got.status_code == 200
    assert got.json()["doc_title"] == "Sample Guide"

    updated = c.put(
        "/admin/knowledge/docs/tax/sample-guide.md",
        json={
            **_payload(),
            "body": "# Sample Guide\n\n## Updated\nUpdated body.",
        },
        headers=ADMIN_HEADERS,
    )
    assert updated.status_code == 200
    assert "Updated body" in updated.json()["body"]
    assert updated.json()["needs_reindex"] is True

    chunks = c.get("/admin/knowledge/docs/tax/sample-guide.md/chunks", headers=ADMIN_HEADERS)
    assert chunks.status_code == 200
    assert chunks.json()["chunks"][0]["metadata"]["doc_id"] == "tax/sample-guide.md"

    deleted = c.delete("/admin/knowledge/docs/tax/sample-guide.md", headers=ADMIN_HEADERS)
    assert deleted.status_code == 200
    assert deleted.json()["doc_id"] == "tax/sample-guide.md"
    assert (service.knowledge_dir / ".trash" / "tax" / "sample-guide.md").exists()
    assert c.get("/admin/knowledge/docs/tax/sample-guide.md", headers=ADMIN_HEADERS).status_code == 404


def test_validate_endpoint_returns_warning_without_hard_source_failure(client):
    c, _service = client

    response = c.post(
        "/admin/knowledge/validate",
        json={
            **_payload(),
            "source_url": "not-a-url",
        },
        headers=ADMIN_HEADERS,
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
        headers=ADMIN_HEADERS,
    )

    assert response.status_code == 400
    assert "filename" in response.json()["detail"]


def test_reindex_endpoint_runs_background_job_with_override(client):
    c, _service = client

    response = c.post("/admin/knowledge/reindex", headers=ADMIN_HEADERS)
    assert response.status_code == 202
    job_id = response.json()["id"]

    job = c.get(f"/admin/ingest/jobs/{job_id}", headers=ADMIN_HEADERS)
    assert job.status_code == 200
    assert job.json()["status"] == "succeeded"
    assert job.json()["chunks_indexed"] == 7


def test_admin_routes_require_token_when_configured(client, monkeypatch):
    c, _service = client
    monkeypatch.setattr(settings, "admin_api_key", "secret-token")

    blocked = c.post("/admin/knowledge/docs", json=_payload())
    assert blocked.status_code == 401

    allowed = c.post(
        "/admin/knowledge/docs",
        json=_payload(),
        headers={"x-admin-token": "secret-token"},
    )
    assert allowed.status_code == 201
