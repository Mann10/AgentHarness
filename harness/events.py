from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
import uuid


@dataclass
class HarnessEvent:
    """Base event with common fields."""
    event_id: str = field(default_factory=lambda: uuid.uuid4().hex)
    timestamp: datetime = field(default_factory=lambda: datetime.now(timezone.utc))


@dataclass
class TurnStarted(HarnessEvent):
    """Emitted when a prompt begins processing by the agent."""
    session_id: str = ""
    prompt: str = ""


@dataclass
class ToolCallEvent(HarnessEvent):
    """Emitted when the agent requests a tool execution."""
    session_id: str = ""
    tool_name: str = ""
    arguments: dict | None = None
    tool_call_id: str = ""


@dataclass
class ToolResultEvent(HarnessEvent):
    """Emitted when a tool call returns a result."""
    session_id: str = ""
    tool_name: str = ""
    result: str = ""
    tool_call_id: str = ""


@dataclass
class ResponseComplete(HarnessEvent):
    """Emitted when the agent finishes a turn with text content."""
    session_id: str = ""
    content: str = ""
    iterations: int = 0
    tool_calls_made: int = 0
    forced: bool = False


@dataclass
class ErrorEvent(HarnessEvent):
    """Emitted when an error occurs during agent execution."""
    session_id: str = ""
    error: str = ""


@dataclass
class CancelledEvent(HarnessEvent):
    """Emitted when a turn is cancelled by the user."""
    session_id: str = ""


@dataclass
class BacklogChangedEvent(HarnessEvent):
    """Emitted when the Scheduler FIFO backlog changes (enqueue / drain / cancel).

    Payload contract: {depth, next_prompt} ONLY (D-06 style) — session_id rides
    on the notification request_id for TUI session-scoping (WR-05 pattern).
    next_prompt is the FULL queued text; truncation is a TUI-presentation concern.
    """
    session_id: str = ""
    depth: int = 0
    next_prompt: str = ""


@dataclass
class SkillLoadedEvent(HarnessEvent):
    """Emitted when a skill body is injected into context (D-07/D-08).

    Fires ONLY on real loads from the shared load_skill() path — never on
    already_loaded (nothing changed), not_found, or cap refusal (load didn't
    happen). session_id is carried for wire request_id consistency; it is NOT
    part of the payload (D-06: {skill} only).
    """
    session_id: str = ""
    skill: str = ""


@dataclass
class TokenProduced(HarnessEvent):
    """Emitted for each chunk of token output during streaming."""
    session_id: str = ""
    chunk: str = ""
    request_id: str = ""


# Event type name constants (for subscriber registration)
EVENT_TURN_STARTED = "TurnStarted"
EVENT_TOOL_CALL = "ToolCallEvent"
EVENT_TOOL_RESULT = "ToolResultEvent"
EVENT_TOKEN_PRODUCED = "TokenProduced"
EVENT_RESPONSE_COMPLETE = "ResponseComplete"
EVENT_ERROR = "ErrorEvent"
EVENT_CANCELLED = "CancelledEvent"
EVENT_SKILL_LOADED = "SkillLoadedEvent"   # name == class name (EventBus routes on type.__name__)
EVENT_BACKLOG_CHANGED = "BacklogChangedEvent"  # name == class name (EventBus routes on type.__name__)
