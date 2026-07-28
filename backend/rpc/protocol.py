from __future__ import annotations

"""JSON-RPC 2.0 message schemas and event type definitions.

Pure data types — no business logic. Uses dataclasses for consistency
with the existing codebase (all harness events use dataclasses).
"""

from dataclasses import dataclass, field
from enum import Enum
from typing import Any


# ── JSON-RPC 2.0 Message Types ──────────────────────────────


@dataclass
class RPCRequest:
    """Incoming JSON-RPC 2.0 request."""
    jsonrpc: str = "2.0"
    id: int | str | None = None
    method: str = ""
    params: dict | None = None


@dataclass
class RPCResponse:
    """Outgoing JSON-RPC 2.0 response (success or error)."""
    jsonrpc: str = "2.0"
    id: int | str | None = None
    result: Any = None
    error: RPCError | None = None


@dataclass
class RPCError:
    """JSON-RPC 2.0 error object."""
    code: int = 0
    message: str = ""
    data: Any = None


# Standard JSON-RPC error codes
PARSE_ERROR = -32700
INVALID_REQUEST = -32600
METHOD_NOT_FOUND = -32601
INVALID_PARAMS = -32602
INTERNAL_ERROR = -32603


@dataclass
class EventPayload:
    """Payload wrapper for event notifications."""
    type: str = ""
    request_id: str = ""
    payload: dict = field(default_factory=dict)


@dataclass
class RPCNotification:
    """JSON-RPC 2.0 notification (no id — no response expected)."""
    jsonrpc: str = "2.0"
    method: str = "event"
    params: EventPayload | None = None


# ── Event Notification Types ────────────────────────────────


class NotificationType(str, Enum):
    """Maps domain event types to notification type strings (D-09)."""
    turn_started = "turn_started"
    tool_call = "tool_call"
    tool_result = "tool_result"
    token = "token"
    response_complete = "response_complete"
    cancelled = "cancelled"
    error = "error"


# ── RPC Method Surface ──────────────────────────────────────

RPC_METHODS: list[str] = [
    "chat",
    "cancel",
    "sessions.list",
    "sessions.switch",
    "sessions.create",
    "sessions.delete",
    "ping",
]
