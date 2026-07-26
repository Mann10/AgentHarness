from __future__ import annotations

"""Harness Runtime -- orchestrator layer for Agent lifecycle, session management, and events."""

# Import non-circular symbols eagerly (these do NOT import from agent)
from harness.event_bus import EventBus
from harness.session_manager import SessionManager
from harness.cancellation import CancellationToken
from harness.events import (
    TurnStarted,
    ToolCallEvent,
    ToolResultEvent,
    ResponseComplete,
    ErrorEvent,
    CancelledEvent,
    HarnessEvent,
    EVENT_TURN_STARTED,
    EVENT_TOOL_CALL,
    EVENT_TOOL_RESULT,
    EVENT_RESPONSE_COMPLETE,
    EVENT_ERROR,
    EVENT_CANCELLED,
)

# Lazy-imported modules (break circular import: agent/core -> harness.events -> harness/__init__ -> {runtime,scheduler} -> agent)
_LAZY_MODULES: dict[str, str] = {
    "RuntimeAPI": "harness.runtime",
    "Scheduler": "harness.scheduler",
}


def __getattr__(name: str):
    """Lazy import for symbols that have circular dependency on agent module."""
    if name in _LAZY_MODULES:
        import importlib
        mod = importlib.import_module(_LAZY_MODULES[name])
        return getattr(mod, name)
    raise AttributeError(f"module 'harness' has no attribute '{name}'")

__all__ = [
    "RuntimeAPI",
    "EventBus",
    "Scheduler",
    "SessionManager",
    "CancellationToken",
    "TurnStarted",
    "ToolCallEvent",
    "ToolResultEvent",
    "ResponseComplete",
    "ErrorEvent",
    "CancelledEvent",
    "HarnessEvent",
    "EVENT_TURN_STARTED",
    "EVENT_TOOL_CALL",
    "EVENT_TOOL_RESULT",
    "EVENT_RESPONSE_COMPLETE",
    "EVENT_ERROR",
    "EVENT_CANCELLED",
]
