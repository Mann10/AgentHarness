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


@dataclass
class ToolResultEvent(HarnessEvent):
    """Emitted when a tool call returns a result."""
    session_id: str = ""
    tool_name: str = ""
    result: str = ""


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


# Event type name constants (for subscriber registration)
EVENT_TURN_STARTED = "TurnStarted"
EVENT_TOOL_CALL = "ToolCallEvent"
EVENT_TOOL_RESULT = "ToolResultEvent"
EVENT_RESPONSE_COMPLETE = "ResponseComplete"
EVENT_ERROR = "ErrorEvent"
EVENT_CANCELLED = "CancelledEvent"
