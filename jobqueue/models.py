from __future__ import annotations

import uuid
from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum


class JobStatus(Enum):
    PENDING = "pending"
    PROCESSING = "processing"
    COMPLETED = "completed"
    FAILED = "failed"


class JobPriority(Enum):
    LOW = 0
    NORMAL = 1
    HIGH = 2


@dataclass
class Job:
    id: str = field(default_factory=lambda: uuid.uuid4().hex)
    prompt: str = ""
    status: JobStatus = JobStatus.PENDING
    priority: JobPriority = JobPriority.NORMAL
    created_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    started_at: datetime | None = None
    completed_at: datetime | None = None
    result: str | None = None
    error: str | None = None
    session_id: str | None = None

    @property
    def short_id(self) -> str:
        return self.id[:8]

    @property
    def prompt_preview(self) -> str:
        if len(self.prompt) <= 60:
            return self.prompt
        return self.prompt[:57] + "..."

    @classmethod
    def from_row(cls, row: dict) -> Job:
        return cls(
            id=row["id"],
            prompt=row["prompt"],
            status=JobStatus(row["status"]),
            priority=JobPriority(row["priority"]),
            created_at=datetime.fromisoformat(row["created_at"]) if row["created_at"] else datetime.now(timezone.utc),
            started_at=datetime.fromisoformat(row["started_at"]) if row.get("started_at") else None,
            completed_at=datetime.fromisoformat(row["completed_at"]) if row.get("completed_at") else None,
            result=row.get("result"),
            error=row.get("error"),
            session_id=row.get("session_id"),
        )

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "prompt": self.prompt,
            "status": self.status.value,
            "priority": self.priority.value,
            "created_at": self.created_at.isoformat(),
            "started_at": self.started_at.isoformat() if self.started_at else None,
            "completed_at": self.completed_at.isoformat() if self.completed_at else None,
            "result": self.result,
            "error": self.error,
            "session_id": self.session_id,
        }
