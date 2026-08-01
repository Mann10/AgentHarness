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
        meta = session.to_snapshot_meta()

        if not path.exists():
            with open(path, "w", encoding="utf-8") as f:
                f.write(json.dumps(meta, ensure_ascii=False) + "\n")
                for ev in session.to_events():
                    f.write(json.dumps(ev, ensure_ascii=False, default=str) + "\n")
        else:
            new_events = session.unpersisted_events()
            stored_meta = self._read_meta(path)
            meta_changed = stored_meta is not None and (
                stored_meta.get("title") != meta["title"]
                or stored_meta.get("metadata") != meta["metadata"]
                or stored_meta.get("updated_at") != meta["updated_at"]
            )
            if meta_changed:
                # Title/metadata changed (e.g. auto-title after first prompt) —
                # rewrite the snapshot line in place, preserving all events.
                with open(path, "w", encoding="utf-8") as f:
                    f.write(json.dumps(meta, ensure_ascii=False) + "\n")
                    for ev in session.to_events():
                        f.write(json.dumps(ev, ensure_ascii=False, default=str) + "\n")
            elif new_events:
                with open(path, "a", encoding="utf-8") as f:
                    for ev in new_events:
                        f.write(json.dumps(ev, ensure_ascii=False, default=str) + "\n")
            else:
                return

        session.mark_saved()

    @staticmethod
    def _read_meta(path: Path) -> dict | None:
        """Read and parse the snapshot meta line (first line) of a JSONL file."""
        try:
            with open(path, "r", encoding="utf-8") as f:
                first = f.readline().strip()
            if not first:
                return None
            return json.loads(first)
        except (OSError, json.JSONDecodeError):
            return None

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
                    lines = [ln.strip() for ln in f if ln.strip()]
                if not lines:
                    continue
                meta = json.loads(lines[0])
                title = meta.get("title")
                if title is None:
                    title = self._fallback_title(lines[1:])
                summaries.append(SessionSummary(
                    id=meta["id"],
                    title=title,
                    created_at=datetime.fromisoformat(meta["created_at"]),
                    updated_at=datetime.fromisoformat(meta["updated_at"]),
                    message_count=len(lines) - 1,
                ))
            except (OSError, json.JSONDecodeError, KeyError) as e:
                logger.warning("Skipping corrupt session file %s: %s", path, e)
        return summaries

    @staticmethod
    def _fallback_title(events: list[str]) -> str | None:
        """Derive a title from the first user message for legacy sessions."""
        from session.models import derive_title
        for line in events:
            try:
                ev = json.loads(line)
            except json.JSONDecodeError:
                continue
            if ev.get("role") == "user" and ev.get("content"):
                return derive_title(ev["content"])
        return None
