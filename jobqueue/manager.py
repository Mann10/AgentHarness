from __future__ import annotations

import asyncio
import logging
from datetime import datetime, timezone

from jobqueue.models import Job, JobPriority, JobStatus
from jobqueue.store import SQLiteJobStore

logger = logging.getLogger(__name__)


class QueueManager:
    def __init__(self, store: SQLiteJobStore | None = None):
        self._store = store or SQLiteJobStore()
        self._queue: asyncio.Queue[Job] = asyncio.Queue()
        self._new_job_event = asyncio.Event()
        self._running = False

    async def start(self) -> None:
        self._running = True
        self._store.reset_in_flight()

    async def shutdown(self) -> None:
        self._running = False
        self._new_job_event.set()
        self._store.close()

    async def enqueue(
        self,
        prompt: str,
        priority: JobPriority = JobPriority.NORMAL,
        session_id: str | None = None,
    ) -> Job:
        job = Job(
            prompt=prompt,
            priority=priority,
            session_id=session_id,
        )
        self._store.enqueue(job)
        await self._queue.put(job)
        self._new_job_event.set()
        logger.info("Enqueued job %s: %s", job.short_id, job.prompt_preview)
        return job

    async def wait_for_job(self) -> Job:
        while self._running:
            try:
                job = await asyncio.wait_for(self._queue.get(), timeout=1.0)
                updated = self._store.dequeue()
                if updated:
                    logger.info("Dequeued job %s: %s", updated.short_id, updated.prompt_preview)
                    return updated
                else:
                    logger.warning("Job %s was stolen or already dequeued", job.short_id)
                    continue
            except asyncio.TimeoutError:
                if not self._store.pending_count():
                    continue
                job_from_db = self._store.dequeue()
                if job_from_db:
                    logger.info("Dequeued stale job %s from DB", job_from_db.short_id)
                    return job_from_db
                continue

    async def complete_job(self, job_id: str, result: str) -> None:
        self._store.complete(job_id, result)
        logger.info("Completed job %s (%d chars)", job_id[:8], len(result))

    async def fail_job(self, job_id: str, error: str) -> None:
        self._store.fail(job_id, error)
        logger.error("Failed job %s: %s", job_id[:8], error[:100])

    def get_job(self, job_id: str) -> Job | None:
        return self._store.get_job(job_id)

    def list_jobs(self, limit: int = 100) -> list[Job]:
        return self._store.list_jobs(limit=limit)

    @property
    def pending_count(self) -> int:
        return self._store.pending_count()
