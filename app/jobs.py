"""A tiny, thread-safe async ingest-job model.

Knowledge-base ingestion (chunk → embed → index into ES + Qdrant) can take a while
and needs no user interaction, so it is exposed as a fire-and-forget job:

    POST /admin/ingest          -> creates a job, runs ingest in the background
    GET  /admin/ingest/jobs     -> list jobs (most recent first)
    GET  /admin/ingest/jobs/{id}-> one job's status

This is a deliberately minimal, single-process implementation: jobs live in an
in-memory registry guarded by a ``threading.Lock``. It is the kind of thing you can
explain end-to-end and later swap for Celery/RQ + a database without changing callers.
"""

from __future__ import annotations

import threading
import uuid
from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from enum import Enum
from typing import Callable


class JobStatus(str, Enum):
    PENDING = "pending"
    RUNNING = "running"
    SUCCEEDED = "succeeded"
    FAILED = "failed"


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


@dataclass
class Job:
    id: str
    status: JobStatus = JobStatus.PENDING
    created_at: str = field(default_factory=_now)
    started_at: str | None = None
    finished_at: str | None = None
    error: str | None = None
    chunks_indexed: int | None = None

    def to_dict(self) -> dict:
        data = asdict(self)
        data["status"] = self.status.value
        return data


class JobRegistry:
    """Thread-safe in-memory registry of ingest jobs (single-process demo)."""

    def __init__(self):
        self._lock = threading.Lock()
        self._jobs: dict[str, Job] = {}

    def create(self) -> Job:
        job = Job(id=str(uuid.uuid4()))
        with self._lock:
            self._jobs[job.id] = job
        return job

    def get(self, job_id: str) -> Job | None:
        with self._lock:
            return self._jobs.get(job_id)

    def list(self) -> list[Job]:
        with self._lock:
            jobs = list(self._jobs.values())
        return sorted(jobs, key=lambda j: j.created_at, reverse=True)

    def _update(self, job_id: str, **changes) -> None:
        with self._lock:
            job = self._jobs.get(job_id)
            if job is None:
                return
            for key, value in changes.items():
                setattr(job, key, value)

    def run(self, job_id: str, ingest_fn: Callable[[], int]) -> None:
        """Run ``ingest_fn`` and record the job lifecycle + result.

        Designed to be handed to ``BackgroundTasks.add_task`` (or any worker). Never
        raises: failures are captured on the job so the API can report them.
        """
        self._update(job_id, status=JobStatus.RUNNING, started_at=_now())
        try:
            count = ingest_fn()
            self._update(
                job_id,
                status=JobStatus.SUCCEEDED,
                finished_at=_now(),
                chunks_indexed=int(count),
            )
        except Exception as exc:  # noqa: BLE001 - capture any ingest failure on the job
            self._update(
                job_id, status=JobStatus.FAILED, finished_at=_now(), error=str(exc)
            )
