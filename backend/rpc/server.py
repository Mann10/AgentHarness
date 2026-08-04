from __future__ import annotations

"""Stdio JSON-RPC 2.0 server with event notification forwarding.

Reads JSON-RPC requests from stdin, dispatches to RuntimeAPI via the
RPCAdapter/Dispatcher pipeline, and writes NDJSON responses to stdout.
All domain events (TurnStarted, ToolCallEvent, etc.) are forwarded as
JSON-RPC notifications with typed payloads per D-08/D-09.
"""

import asyncio
import json
import logging
import sys
from dataclasses import asdict
from typing import Any

from backend.rpc.adapter import RPCAdapter
from backend.rpc.dispatcher import Dispatcher
from backend.rpc.protocol import (
    RPCNotification,
    RPCRequest,
    RPCResponse,
    EventPayload,
    NotificationType,
    PARSE_ERROR,
    RPCError,
)
from harness.event_bus import EventBus
from harness.events import (
    HarnessEvent,
    TurnStarted,
    ToolCallEvent,
    ToolResultEvent,
    TokenProduced,
    ResponseComplete,
    CancelledEvent,
    ErrorEvent,
    SkillLoadedEvent,
    EVENT_TURN_STARTED,
    EVENT_TOOL_CALL,
    EVENT_TOOL_RESULT,
    EVENT_TOKEN_PRODUCED,
    EVENT_RESPONSE_COMPLETE,
    EVENT_CANCELLED,
    EVENT_ERROR,
    EVENT_SKILL_LOADED,
)
from harness.runtime import RuntimeAPI

logger = logging.getLogger(__name__)

# ── Domain event type → notification type mapping (D-09) ────

_DOMAIN_TO_NOTIFICATION: dict[str, str] = {
    EVENT_TURN_STARTED: NotificationType.turn_started.value,
    EVENT_TOOL_CALL: NotificationType.tool_call.value,
    EVENT_TOOL_RESULT: NotificationType.tool_result.value,
    EVENT_TOKEN_PRODUCED: NotificationType.token.value,
    EVENT_RESPONSE_COMPLETE: NotificationType.response_complete.value,
    EVENT_CANCELLED: NotificationType.cancelled.value,
    EVENT_ERROR: NotificationType.error.value,
    EVENT_SKILL_LOADED: NotificationType.skill_loaded.value,
}

# ── Payload extraction helpers ──────────────────────────────


def _extract_turn_started_payload(event: TurnStarted) -> dict:
    return {"session_id": event.session_id, "prompt": event.prompt}


def _extract_tool_call_payload(event: ToolCallEvent) -> dict:
    return {
        "session_id": event.session_id,
        "tool_name": event.tool_name,
        "arguments": event.arguments,
        "tool_call_id": event.tool_call_id,
    }


def _extract_tool_result_payload(event: ToolResultEvent) -> dict:
    return {
        "session_id": event.session_id,
        "tool_name": event.tool_name,
        "result": event.result,
        "tool_call_id": event.tool_call_id,
    }


def _extract_token_produced_payload(event: TokenProduced) -> dict:
    return {
        "session_id": event.session_id,
        "chunk": event.chunk,
        "request_id": event.request_id,
    }


def _extract_response_complete_payload(event: ResponseComplete) -> dict:
    return {
        "session_id": event.session_id,
        "content": event.content,
        "iterations": event.iterations,
        "tool_calls_made": event.tool_calls_made,
        "forced": event.forced,
    }


def _extract_cancelled_payload(event: CancelledEvent) -> dict:
    return {"session_id": event.session_id}


def _extract_skill_loaded_payload(event: SkillLoadedEvent) -> dict:
    """D-06: payload is {skill: canonical name} ONLY — status lives in the RPC ack."""
    return {"skill": event.skill}


def _extract_error_payload(event: ErrorEvent) -> dict:
    return {"session_id": event.session_id, "error": event.error}


# Map domain event type to payload extractor
_PAYLOAD_EXTRACTORS: dict[str, callable] = {
    EVENT_TURN_STARTED: _extract_turn_started_payload,
    EVENT_TOOL_CALL: _extract_tool_call_payload,
    EVENT_TOOL_RESULT: _extract_tool_result_payload,
    EVENT_TOKEN_PRODUCED: _extract_token_produced_payload,
    EVENT_RESPONSE_COMPLETE: _extract_response_complete_payload,
    EVENT_CANCELLED: _extract_cancelled_payload,
    EVENT_ERROR: _extract_error_payload,
    EVENT_SKILL_LOADED: _extract_skill_loaded_payload,
}


def _write_json(obj: Any) -> None:
    """Serialize object to JSON and write as NDJSON to stdout, then flush."""
    from dataclasses import asdict, is_dataclass
    data = asdict(obj) if is_dataclass(obj) else obj
    sys.stdout.write(json.dumps(data, default=str) + "\n")
    sys.stdout.flush()


# ── Server ──────────────────────────────────────────────────


class RPCServer:
    """JSON-RPC 2.0 server over stdin/stdout with event notification forwarding.

    Reads requests from stdin, dispatches to RuntimeAPI via RPCAdapter,
    writes responses to stdout, and forwards all domain events as NDJSON
    notifications.
    """

    def __init__(self, runtime: RuntimeAPI) -> None:
        self._runtime = runtime
        self._event_bus: EventBus = runtime.event_bus

        self._dispatcher = Dispatcher()
        self._adapter = RPCAdapter(runtime)
        self._adapter.register_all(self._dispatcher)

        self._running: bool = False
        self._read_task: asyncio.Task | None = None

    async def start(self) -> None:
        """Start the RPCServer: subscribe to events and begin reading stdin."""
        self._running = True

        # Subscribe to all domain events for notification forwarding
        await self._event_bus.subscribe(EVENT_TURN_STARTED, self._on_event)
        await self._event_bus.subscribe(EVENT_TOOL_CALL, self._on_event)
        await self._event_bus.subscribe(EVENT_TOOL_RESULT, self._on_event)
        await self._event_bus.subscribe(EVENT_TOKEN_PRODUCED, self._on_event)
        await self._event_bus.subscribe(EVENT_RESPONSE_COMPLETE, self._on_event)
        await self._event_bus.subscribe(EVENT_CANCELLED, self._on_event)
        await self._event_bus.subscribe(EVENT_ERROR, self._on_event)
        await self._event_bus.subscribe(EVENT_SKILL_LOADED, self._on_event)

        # Start reading stdin loop
        self._read_task = asyncio.create_task(self._read_loop())
        logger.info("RPCServer started")

    async def shutdown(self) -> None:
        """Shutdown: unsubscribe events and cancel the read loop."""
        self._running = False

        await self._event_bus.unsubscribe(EVENT_TURN_STARTED, self._on_event)
        await self._event_bus.unsubscribe(EVENT_TOOL_CALL, self._on_event)
        await self._event_bus.unsubscribe(EVENT_TOOL_RESULT, self._on_event)
        await self._event_bus.unsubscribe(EVENT_TOKEN_PRODUCED, self._on_event)
        await self._event_bus.unsubscribe(EVENT_RESPONSE_COMPLETE, self._on_event)
        await self._event_bus.unsubscribe(EVENT_CANCELLED, self._on_event)
        await self._event_bus.unsubscribe(EVENT_ERROR, self._on_event)
        await self._event_bus.unsubscribe(EVENT_SKILL_LOADED, self._on_event)

        if self._read_task is not None and not self._read_task.done():
            self._read_task.cancel()
            try:
                await self._read_task
            except asyncio.CancelledError:
                pass

        sys.stdout.flush()
        logger.info("RPCServer shut down")

    # ── Event notification forwarding ───────────────────────

    async def _on_event(self, event: HarnessEvent) -> None:
        """Callback for EventBus events — forwards as JSON-RPC notification."""
        notification = self._event_to_notification(event)
        _write_json(notification)

    def _event_to_notification(self, event: HarnessEvent) -> dict:
        """Convert a domain event to a JSON-RPC notification dict.

        Maps domain event type to notification type string (D-09),
        extracts relevant payload fields, and wraps in the standard
        notification format (D-08):
            {"jsonrpc":"2.0","method":"event","params":{"type":"...","request_id":"...","payload":{...}}}
        """
        domain_type = type(event).__name__
        notification_type = _DOMAIN_TO_NOTIFICATION.get(domain_type, domain_type.lower())

        # Determine request_id — use session_id as primary, event_id as fallback
        request_id = getattr(event, "session_id", "") or event.event_id

        # Extract payload using registered extractor
        extractor = _PAYLOAD_EXTRACTORS.get(domain_type)
        if extractor is not None:
            payload = extractor(event)
        else:
            # Fallback: use dataclass asdict for unknown event types
            payload = asdict(event)

        notification = {
            "jsonrpc": "2.0",
            "method": "event",
            "params": {
                "type": notification_type,
                "request_id": request_id,
                "payload": payload,
            },
        }
        return notification

    # ── Request read loop ───────────────────────────────────

    async def _read_loop(self) -> None:
        """Read JSON-RPC requests from stdin line by line.

        Each line is parsed as JSON, validated as an RPCRequest,
        dispatched to the method handler, and the response is
        written back as NDJSON to stdout.
        """
        while self._running:
            try:
                line = await asyncio.to_thread(sys.stdin.readline)
            except (ValueError, OSError) as exc:
                logger.error("Stdin read error: %s", exc)
                break

            if not line:
                # EOF — stdin closed by the client
                logger.info("Stdin closed — shutting down RPC server")
                self._running = False
                break

            line = line.strip()
            if not line:
                continue

            # Parse JSON
            try:
                raw = json.loads(line)
            except json.JSONDecodeError as exc:
                _write_json({
                    "jsonrpc": "2.0",
                    "id": None,
                    "error": {
                        "code": PARSE_ERROR,
                        "message": f"Parse error: {exc}",
                    },
                })
                continue

            # Validate as RPCRequest
            if not isinstance(raw, dict) or "method" not in raw:
                _write_json({
                    "jsonrpc": "2.0",
                    "id": raw.get("id") if isinstance(raw, dict) else None,
                    "error": {
                        "code": -32600,
                        "message": "Invalid Request: missing 'method'",
                    },
                })
                continue

            request = RPCRequest(
                jsonrpc=raw.get("jsonrpc", "2.0"),
                id=raw.get("id"),
                method=raw["method"],
                params=raw.get("params"),
            )

            # Dispatch and write response
            response = await self._dispatcher.dispatch(request)
            _write_json(response)
