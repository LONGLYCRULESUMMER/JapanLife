import threading

from app.jobs import JobRegistry, JobStatus


def test_create_returns_pending_job_with_id():
    reg = JobRegistry()
    job = reg.create()
    assert job.id
    assert job.status == JobStatus.PENDING
    assert job.created_at
    assert reg.get(job.id) is job


def test_run_success_records_result():
    reg = JobRegistry()
    job = reg.create()
    reg.run(job.id, lambda: 42)
    done = reg.get(job.id)
    assert done.status == JobStatus.SUCCEEDED
    assert done.chunks_indexed == 42
    assert done.started_at and done.finished_at
    assert done.error is None


def test_run_failure_captures_error():
    reg = JobRegistry()
    job = reg.create()

    def boom():
        raise RuntimeError("es down")

    reg.run(job.id, boom)
    failed = reg.get(job.id)
    assert failed.status == JobStatus.FAILED
    assert "es down" in failed.error
    assert failed.chunks_indexed is None
    assert failed.finished_at


def test_get_unknown_returns_none():
    assert JobRegistry().get("nope") is None


def test_list_contains_all_jobs():
    reg = JobRegistry()
    a, b = reg.create(), reg.create()
    ids = {j.id for j in reg.list()}
    assert ids == {a.id, b.id}


def test_to_dict_serializes_status_as_plain_string():
    job = JobRegistry().create()
    data = job.to_dict()
    assert data["status"] == "pending"
    assert set(data) >= {
        "id", "status", "created_at", "started_at", "finished_at", "error", "chunks_indexed"
    }


def test_concurrent_creates_are_thread_safe():
    reg = JobRegistry()

    def worker():
        for _ in range(50):
            reg.create()

    threads = [threading.Thread(target=worker) for _ in range(8)]
    for t in threads:
        t.start()
    for t in threads:
        t.join()
    assert len(reg.list()) == 8 * 50
