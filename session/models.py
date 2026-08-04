from __future__ import annotations

import os
import uuid
from dataclasses import dataclass, field, asdict
from datetime import datetime
from pathlib import Path
from collections.abc import Awaitable, Callable

from context.context import ConversationContext
from context.message import Message


TITLE_MAX_CHARS = 15


def derive_title(text: str) -> str:
    """Derive a session title from a prompt: first line, truncated to 15 chars.

    Matches the user-facing rule: title = first line of what the user wrote,
    truncated to TITLE_MAX_CHARS characters with a trailing "..." when longer.
    """
    first_line = text.strip().splitlines()[0] if text.strip() else ""
    if len(first_line) > TITLE_MAX_CHARS:
        return first_line[:TITLE_MAX_CHARS] + "..."
    return first_line


@dataclass
class SessionSummary:
    id: str
    title: str | None
    created_at: datetime
    updated_at: datetime
    message_count: int


@dataclass
class Session:
    id: str
    system_prompt: str
    title: str | None = None
    created_at: datetime = field(default_factory=datetime.now)
    updated_at: datetime = field(default_factory=datetime.now)
    metadata: dict = field(default_factory=dict)
    skill_manifest: str | None = None
    skill_state: dict = field(default_factory=dict)  # Phase 12 pattern — non-serialized by construction
    _context: ConversationContext | None = None
    # Identity watermark of already-persisted messages, as {id(msg): msg}.
    # Keying by identity (not position) survives summarization removing
    # saved messages between saves (CR-01). The dict VALUES hold strong
    # references so an id() can never be garbage-collected and reused by a
    # new message — a bare {id(m)} set would wrongly mark a brand-new
    # message as saved and drop it from the JSONL file.
    _saved_messages: dict = field(default_factory=dict)

    @property
    def context(self) -> ConversationContext:
        if self._context is None:
            raise RuntimeError("Session context not restored")
        return self._context

    # ── Assembly ──────────────────────────────────────────

    def to_llm_messages(self) -> list[dict]:
        system_block = self._build_system_prompt()
        msgs = [{"role": "system", "content": system_block}]
        msgs.extend(self._context.to_llm_messages())
        return msgs

    def _build_system_prompt(self) -> str:
        parts = [self.system_prompt]
        agents_md = Path("AGENTS.md")
        if agents_md.exists():
            parts.append(f"# Project Instructions\n\n{agents_md.read_text()}")
        parts.append(f"# Environment\nCWD: {os.getcwd()}")
        # D-11/D-12/D-13: budgeted skills manifest, appended last, omitted when empty.
        if self.skill_manifest:
            parts.append(self.skill_manifest)
        return "\n\n---\n\n".join(parts)

    # ── Serialization ─────────────────────────────────────

    def to_events(self) -> list[dict]:
        return [self._message_to_event(m) for m in self._context._messages if m.persist]

    @staticmethod
    def _message_to_event(msg: Message) -> dict:
        d = {"role": msg.role, "content": msg.content, "token_count": msg.token_count}
        if msg.tool_calls:
            d["tool_calls"] = [asdict(tc) for tc in msg.tool_calls]
        if msg.tool_call_id:
            d["tool_call_id"] = msg.tool_call_id
        return d

    def get_messages(self) -> list[dict]:
        """Return conversation messages as serializable dicts in chronological order.

        Works for live sessions (restored context) AND store-loaded sessions
        (raw stored events). Never raises on a non-restored session — the
        AttributeError in to_events() on _context=None is exactly the bug this
        accessor exists to avoid (research finding, empirically confirmed).
        """
        if self._context is not None:
            return self.to_events()
        return [dict(e) for e in getattr(self, "_stored_events", [])]

    def unpersisted_events(self) -> list[dict]:
        if self._context is None:
            return []
        saved = getattr(self, "_saved_messages", {})
        events = []
        for msg in self._context._messages:
            if msg.persist and id(msg) not in saved:
                events.append(self._message_to_event(msg))
        return events

    def mark_saved(self) -> None:
        if self._context is not None:
            # Watermark by message identity, not position: survives
            # summarization removing already-saved messages between saves (CR-01).
            self._saved_messages = {id(m): m for m in self._context._messages}

    def to_snapshot_meta(self) -> dict:
        return {
            "type": "meta",
            "id": self.id,
            "title": self.title,
            "created_at": self.created_at.isoformat(),
            "updated_at": self.updated_at.isoformat(),
            "system_prompt": self.system_prompt,
            "metadata": self.metadata,
        }

    @classmethod
    def from_events(cls, events: list[dict]) -> Session:
        meta = events[0]
        session = cls(
            id=meta["id"],
            system_prompt=meta["system_prompt"],
            title=meta.get("title"),
            created_at=datetime.fromisoformat(meta["created_at"]),
            updated_at=datetime.fromisoformat(meta["updated_at"]),
            metadata=meta.get("metadata", {}),
            _context=None,
        )
        session._stored_events = [e for e in events[1:]]
        return session

    async def restore_context(
        self,
        count_tokens: Callable[[str], int],
        token_limit: int,
        summarize_fn: Callable[[list[dict]], Awaitable[str]] | None = None,
        summarize_threshold: float = 0.75,
        keep_recent_exchanges: int = 2,
    ) -> None:
        ctx = ConversationContext(
            count_tokens=count_tokens,
            token_limit=token_limit,
            summarize_fn=summarize_fn,
            summarize_threshold=summarize_threshold,
            keep_recent_exchanges=keep_recent_exchanges,
        )
        for e in self._stored_events:
            msg = Message.from_dict(e)
            await ctx.add_message(msg)
        self._context = ctx
        # Seed the identity watermark: every replayed event is already on disk,
        # so all live messages count as saved (CR-01 consistency with mark_saved).
        self._saved_messages = {id(m): m for m in self._context._messages}
        del self._stored_events

    @classmethod
    def create(
        cls,
        system_prompt: str,
        count_tokens: Callable[[str], int],
        token_limit: int,
        summarize_fn: Callable[[list[dict]], Awaitable[str]] | None = None,
        summarize_threshold: float = 0.75,
        keep_recent_exchanges: int = 2,
    ) -> Session:
        ctx = ConversationContext(
            count_tokens=count_tokens,
            token_limit=token_limit,
            summarize_fn=summarize_fn,
            summarize_threshold=summarize_threshold,
            keep_recent_exchanges=keep_recent_exchanges,
        )
        return cls(
            id=uuid.uuid4().hex,
            system_prompt=system_prompt,
            _context=ctx,
        )
