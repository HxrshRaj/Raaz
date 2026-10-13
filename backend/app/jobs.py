"""Background job runner.

An in-process thread pool with **persisted** job state, bounded retries with exponential backoff, and metrics.
This is deliberately not Celery: for a single-node modular monolith it gives the same observable guarantees
(status, attempts, failure reporting) with no extra moving parts. See docs/ARCHITECTURE.md for when to swap in
Celery/RQ + Redis (multiple API nodes, long jobs, or independent worker scaling).
"""

from __future__ import annotations

import threading
import time
from collections.abc import Callable
from concurrent.futures import ThreadPoolExecutor
from datetime import UTC, datetime
from typing import Any

from . import db as dbmod
from . import metrics
from .logging_setup import get_logger
from .models import Job

log = get_logger("raaz.jobs")

_pool: ThreadPoolExecutor | None = None
_lock = threading.Lock()


def _executor() -> ThreadPoolExecutor:
    global _pool
    with _lock:
        if _pool is None:
            _pool = ThreadPoolExecutor(max_workers=4, thread_name_prefix="raaz-job")
        return _pool


def submit(kind: str, fn: Callable[[], dict[str, Any] | None], *, session_id: str | None = None, max_attempts: int = 3,
           base_delay: float = 0.5, retry_on: tuple[type[BaseException], ...] = (TimeoutError, ConnectionError)) -> str:
    with dbmod.SessionLocal() as db:
        job = Job(kind=kind, session_id=session_id, status="queued")
        db.add(job)
        db.commit()
        job_id = job.id

    def run() -> None:
        for attempt in range(1, max_attempts + 1):
            with dbmod.SessionLocal() as db:
                j = db.get(Job, job_id)
                j.status, j.attempts = "running", attempt  # type: ignore[union-attr]
                db.commit()
            t0 = time.perf_counter()
            try:
                result = fn() or {}
                with dbmod.SessionLocal() as db:
                    j = db.get(Job, job_id)
                    j.status, j.result, j.finished_at = "succeeded", result, datetime.now(UTC)  # type: ignore[union-attr]
                    db.commit()
                metrics.inc("raaz_jobs_total", kind=kind, status="succeeded")
                metrics.observe("raaz_job_seconds", time.perf_counter() - t0, kind=kind)
                return
            except retry_on as e:
                log.warning("job transient failure", extra={"job": job_id, "kind": kind, "attempt": attempt, "error": str(e)})
                if attempt < max_attempts:
                    time.sleep(base_delay * (2 ** (attempt - 1)))
                    continue
                _fail(job_id, kind, e)
                return
            except Exception as e:  # noqa: BLE001
                _fail(job_id, kind, e)
                return

    _executor().submit(run)
    return job_id


def _fail(job_id: str, kind: str, e: BaseException) -> None:
    log.error("job failed", extra={"job": job_id, "kind": kind, "error": repr(e)})
    with dbmod.SessionLocal() as db:
        j = db.get(Job, job_id)
        j.status, j.error, j.finished_at = "failed", f"{type(e).__name__}: {e}"[:500], datetime.now(UTC)  # type: ignore[union-attr]
        db.commit()
    metrics.inc("raaz_jobs_total", kind=kind, status="failed")


def wait(job_id: str, timeout: float = 20.0) -> Job:
    end = time.time() + timeout
    while time.time() < end:
        with dbmod.SessionLocal() as db:
            j = db.get(Job, job_id)
            if j and j.status in ("succeeded", "failed"):
                return j
        time.sleep(0.05)
    raise TimeoutError(job_id)


def shutdown_jobs() -> None:
    global _pool
    with _lock:
        if _pool is not None:
            _pool.shutdown(wait=True, cancel_futures=False)
            _pool = None
