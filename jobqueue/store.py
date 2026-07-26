from __future__ import annotations

import logging
import sqlite3
from datetime import datetime, timezone
from pathlib import Path

from jobqueue.models import Job, JobStatus, JobPriority

logger = logging.getLogger(__name__)

_SCHEMA = """
CREATE TABLE IF NOT EXISTS jobs (
    id TEXT PRIMARY KEY,
    prompt TEXT NOT NULL,
    status TEXT NOT NULL DEFAULT 'pending',
    priority INTEGER NOT NULL DEFAULT 1,
    created_at TEXT NOT NULL,
    started_at TEXT,
    completed_at TEXT,
    result TEXT,
    error TEXT,
    session_id TEXT
);

CREATE INDEX IF NOT EXISTS idx_jobs_status ON jobs(status);
CREATE INDEX IF NOT EXISTS idx_jobs_priority ON jobs(priority);
"""


class SQLiteJobStore:
    def __init__(self, db_path: str | None = None):
        if db_path is None:
            db_path = str(Path.cwd() / ".agentharness" / "queue.db")
        Path(db_path).parent.mkdir(parents=True, exist_ok=True)
        self._db_path = db_path
        self._conn: sqlite3.Connection | None = None

    def _get_conn(self) -> sqlite3.Connection:
        if self._conn is None:
            self._conn = sqlite3.connect(self._db_path)
            self._conn.row_factory = sqlite3.Row
            self._conn.execute("PRAGMA journal_mode=WAL")
            self._conn.executescript(_SCHEMA)
        return self._conn

    def enqueue(self, job: Job) -> None:
        conn = self._get_conn()
        conn.execute(
            "INSERT OR REPLACE INTO jobs (id, prompt, status, priority, created_at, session_id) "
            "VALUES (?, ?, ?, ?, ?, ?)",
            (job.id, job.prompt, job.status.value, job.priority.value,
             job.created_at.isoformat(), job.session_id),
        )
        conn.commit()

    def dequeue(self) -> Job | None:
        conn = self._get_conn()
        cursor = conn.execute(
            "SELECT * FROM jobs WHERE status = ? ORDER BY priority DESC, created_at ASC LIMIT 1",
            (JobStatus.PENDING.value,),
        )
        row = cursor.fetchone()
        if row is None:
            return None
        job = Job.from_row(dict(row))
        conn.execute(
            "UPDATE jobs SET status = ?, started_at = ? WHERE id = ? AND status = ?",
            (JobStatus.PROCESSING.value, datetime.now(timezone.utc).isoformat(),
             job.id, JobStatus.PENDING.value),
        )
        conn.commit()
        cursor2 = conn.execute("SELECT * FROM jobs WHERE id = ?", (job.id,))
        updated = cursor2.fetchone()
        if updated is None:
            return None
        return Job.from_row(dict(updated))

    def complete(self, job_id: str, result: str) -> None:
        conn = self._get_conn()
        conn.execute(
            "UPDATE jobs SET status = ?, result = ?, completed_at = ? WHERE id = ?",
            (JobStatus.COMPLETED.value, result, datetime.now(timezone.utc).isoformat(), job_id),
        )
        conn.commit()

    def fail(self, job_id: str, error: str) -> None:
        conn = self._get_conn()
        conn.execute(
            "UPDATE jobs SET status = ?, error = ?, completed_at = ? WHERE id = ?",
            (JobStatus.FAILED.value, error, datetime.now(timezone.utc).isoformat(), job_id),
        )
        conn.commit()

    def get_job(self, job_id: str) -> Job | None:
        conn = self._get_conn()
        cursor = conn.execute("SELECT * FROM jobs WHERE id = ?", (job_id,))
        row = cursor.fetchone()
        return Job.from_row(dict(row)) if row else None

    def list_jobs(self, limit: int = 100, offset: int = 0) -> list[Job]:
        conn = self._get_conn()
        cursor = conn.execute(
            "SELECT * FROM jobs ORDER BY created_at DESC LIMIT ? OFFSET ?",
            (limit, offset),
        )
        return [Job.from_row(dict(row)) for row in cursor.fetchall()]

    def reset_in_flight(self) -> int:
        conn = self._get_conn()
        cursor = conn.execute(
            "UPDATE jobs SET status = ?, started_at = NULL "
            "WHERE status = ?",
            (JobStatus.PENDING.value, JobStatus.PROCESSING.value),
        )
        conn.commit()
        return cursor.rowcount

    def pending_count(self) -> int:
        conn = self._get_conn()
        cursor = conn.execute(
            "SELECT COUNT(*) FROM jobs WHERE status = ?",
            (JobStatus.PENDING.value,),
        )
        return cursor.fetchone()[0]

    def close(self) -> None:
        if self._conn:
            self._conn.close()
            self._conn = None
