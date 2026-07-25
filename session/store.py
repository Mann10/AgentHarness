from __future__ import annotations

import hashlib
import json
import logging
import os
from abc import ABC, abstractmethod
from datetime import datetime
from pathlib import Path

from session.models import Session, SessionSummary

logger = logging.getLogger(__name__)


class SessionStore(ABC):

    @abstractmethod
    async def save(self, session: Session) -> None: ...

    @abstractmethod
    async def load(self, session_id: str) -> Session | None: ...

    @abstractmethod
    async def delete(self, session_id: str) -> None: ...

    @abstractmethod
    async def list_sessions(self) -> list[SessionSummary]: ...


class JSONLSessionStore(SessionStore):

    def __init__(self, base_dir: str | None = None):
        if base_dir is None:
            base_dir = Path.cwd() / ".agentharness"
        self._dir = Path(base_dir)
        self._dir.mkdir(parents=True, exist_ok=True)

    def _path(self, session_id: str) -> Path:
        return self._dir / f"{session_id}.jsonl"

    async def save(self, session: Session) -> None:
        path = self._path(session.id)

        if not path.exists():
            with open(path, "w", encoding="utf-8") as f:
                f.write(json.dumps(session.to_snapshot_meta(), ensure_ascii=False) + "\n")
                for ev in session.to_events():
                    f.write(json.dumps(ev, ensure_ascii=False, default=str) + "\n")
        else:
            new_events = session.unpersisted_events()
            if not new_events:
                return
            with open(path, "a", encoding="utf-8") as f:
                for ev in new_events:
                    f.write(json.dumps(ev, ensure_ascii=False, default=str) + "\n")

        session.mark_saved()

    async def load(self, session_id: str) -> Session | None:
        path = self._path(session_id)
        if not path.exists():
            return None
        try:
            events = []
            with open(path, "r", encoding="utf-8") as f:
                for line in f:
                    line = line.strip()
                    if line:
                        events.append(json.loads(line))
            if not events:
                return None
            return Session.from_events(events)
        except (json.JSONDecodeError, KeyError) as e:
            logger.warning("Corrupt session file %s: %s", session_id, e)
            return None

    async def delete(self, session_id: str) -> None:
        self._path(session_id).unlink(missing_ok=True)

    async def list_sessions(self) -> list[SessionSummary]:
        summaries = []
        for path in sorted(self._dir.glob("*.jsonl")):
            try:
                with open(path, "r", encoding="utf-8") as f:
                    first_line = f.readline().strip()
                if not first_line:
                    continue
                meta = json.loads(first_line)
                msg_count = 0
                with open(path, "r", encoding="utf-8") as f:
                    f.readline()
                    for line in f:
                        if line.strip():
                            msg_count += 1
                summaries.append(SessionSummary(
                    id=meta["id"],
                    title=meta.get("title"),
                    created_at=datetime.fromisoformat(meta["created_at"]),
                    updated_at=datetime.fromisoformat(meta["updated_at"]),
                    message_count=msg_count,
                ))
            except (OSError, json.JSONDecodeError, KeyError) as e:
                logger.warning("Skipping corrupt session file %s: %s", path, e)
        return summaries
