import pytest
from fastapi.testclient import TestClient

from app.jobs import JobRegistry
from app.main import app
from app.routes import get_ingest_fn, get_job_registry
from core.config import settings


@pytest.fixture
def client(monkeypatch):
    monkeypatch.setattr(settings, "deepseek_api_key", "test-key-not-used")
    registry = JobRegistry()
    app.dependency_overrides[get_job_registry] = lambda: registry
    with TestClient(app) as c:
        yield c
    app.dependency_overrides.clear()


def test_trigger_ingest_runs_job_and_reports_success(client):
    app.dependency_overrides[get_ingest_fn] = lambda: (lambda: 156)
    r = client.post("/admin/ingest")
    assert r.status_code == 202
    job = r.json()
    assert "id" in job and job["status"] in ("pending", "running", "succeeded")

    # Under TestClient the background task has already run.
    got = client.get(f"/admin/ingest/jobs/{job['id']}").json()
    assert got["status"] == "succeeded"
    assert got["chunks_indexed"] == 156
    assert got["started_at"] and got["finished_at"]
    assert got["error"] is None


def test_trigger_ingest_failure_is_captured(client):
    def boom():
        raise RuntimeError("qdrant unreachable")

    app.dependency_overrides[get_ingest_fn] = lambda: boom
    job_id = client.post("/admin/ingest").json()["id"]

    got = client.get(f"/admin/ingest/jobs/{job_id}").json()
    assert got["status"] == "failed"
    assert "qdrant unreachable" in got["error"]
    assert got["chunks_indexed"] is None


def test_list_jobs_returns_all(client):
    app.dependency_overrides[get_ingest_fn] = lambda: (lambda: 1)
    client.post("/admin/ingest")
    client.post("/admin/ingest")
    jobs = client.get("/admin/ingest/jobs").json()["jobs"]
    assert len(jobs) == 2


def test_unknown_job_returns_404(client):
    r = client.get("/admin/ingest/jobs/does-not-exist")
    assert r.status_code == 404
