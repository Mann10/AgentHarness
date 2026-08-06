from __future__ import annotations

import asyncio
from unittest.mock import MagicMock

import pytest

from backend.rpc.server import RPCServer
from harness.event_bus import EventBus
from harness.events import EVENT_BACKLOG_CHANGED, BacklogChangedEvent
from harness.scheduler import Scheduler
from tests.conftest import StubAgent


@pytest.fixture
async def bus() -> EventBus:
    return EventBus()


# -- Dimension 1: emission on enqueue / drain / cancel (D-v10) ---------------


@pytest.mark.asyncio
async def test_enqueue_emits_backlog_changed() -> None:
    """submitting while busy queues to the backlog and emits exactly one
    BacklogChangedEvent with depth == 1 and next_prompt == the queued text."""
    bus = EventBus()
    received: list = []

    async def collector(event) -> None:
        received.append(event)

    await bus.subscribe("BacklogChangedEvent", collector)

    agent = StubAgent(delay=0.5)
    s = Scheduler(agent, bus)
    await s.start()

    await s.submit_prompt("first")
    await asyncio.sleep(0.05)  # let the first turn start
    await s.submit_prompt("second")

    assert len(received) == 1
    assert isinstance(received[0], BacklogChangedEvent)
    assert received[0].depth == 1
    assert received[0].next_prompt == "second"
    await s.shutdown()


@pytest.mark.asyncio
async def test_multiple_enqueues_emit_depth_and_head() -> None:
    """Two queued prompts emit depth == 2 with next_prompt == the FIRST queued
    text (FIFO head read from the mirror deque — asyncio.Queue cannot peek)."""
    bus = EventBus()
    received: list = []

    async def collector(event) -> None:
        received.append(event)

    await bus.subscribe("BacklogChangedEvent", collector)

    agent = StubAgent(delay=0.5)
    s = Scheduler(agent, bus)
    await s.start()

    await s.submit_prompt("first")
    await asyncio.sleep(0.05)  # let the first turn start
    await s.submit_prompt("second")
    await s.submit_prompt("third")

    assert len(received) == 2
    assert isinstance(received[-1], BacklogChangedEvent)
    assert received[-1].depth == 2
    assert received[-1].next_prompt == "second"  # FIFO head, not the newest
    await s.shutdown()


@pytest.mark.asyncio
async def test_drain_emits_zero_when_last_prompt_starts() -> None:
    """When the last queued prompt starts, the drain emits depth == 0 with
    next_prompt == "" — the TUI panel hides at depth zero."""
    bus = EventBus()
    received: list = []

    async def collector(event) -> None:
        received.append(event)

    await bus.subscribe("BacklogChangedEvent", collector)

    agent = StubAgent(delay=0.1)
    s = Scheduler(agent, bus)
    await s.start()

    await s.submit_prompt("first")
    await asyncio.sleep(0.05)  # let the first turn start
    await s.submit_prompt("second")  # enqueue event: depth 1

    # Wait for the first turn to complete and drain to start "second"
    await asyncio.sleep(0.5)

    assert s.backlog_size == 0
    assert isinstance(received[-1], BacklogChangedEvent)
    assert received[-1].depth == 0
    assert received[-1].next_prompt == ""
    await s.shutdown()


@pytest.mark.asyncio
async def test_cancel_clears_backlog_and_emits_zero() -> None:
    """cancel() clears the queued backlog and emits depth == 0 so the TUI
    panel hides — queued prompts under a cancelled turn never execute."""
    bus = EventBus()
    received: list = []

    async def collector(event) -> None:
        received.append(event)

    await bus.subscribe("BacklogChangedEvent", collector)

    agent = StubAgent(delay=1.0)
    s = Scheduler(agent, bus)
    await s.start()

    await s.submit_prompt("long task")
    await asyncio.sleep(0.05)  # let it start
    await s.submit_prompt("queued one")
    await s.submit_prompt("queued two")

    await s.cancel()
    await asyncio.sleep(0.2)

    assert s.backlog_size == 0
    assert isinstance(received[-1], BacklogChangedEvent)
    assert received[-1].depth == 0
    assert received[-1].next_prompt == ""
    await s.shutdown()


# -- Dimension 2: exact wire format (D-v10, {depth, next_prompt} only) --------


@pytest.mark.asyncio
async def test_event_maps_to_notification_wire_format() -> None:
    """BacklogChangedEvent maps to the exact JSON-RPC notification dict the TUI
    parses: type=backlog_changed, request_id=session_id, payload={depth, next_prompt}."""
    server = RPCServer(MagicMock())
    notif = server._event_to_notification(
        BacklogChangedEvent(session_id="sess-1", depth=2, next_prompt="fix the bug")
    )
    assert notif == {
        "jsonrpc": "2.0",
        "method": "event",
        "params": {
            "type": "backlog_changed",
            "request_id": "sess-1",
            "payload": {"depth": 2, "next_prompt": "fix the bug"},
        },
    }


@pytest.mark.asyncio
async def test_payload_is_depth_and_next_prompt_only() -> None:
    """D-v10: the notification payload has exactly the 'depth' and 'next_prompt'
    keys — no session_id, no event_id leak (session rides on request_id)."""
    server = RPCServer(MagicMock())
    notif = server._event_to_notification(
        BacklogChangedEvent(session_id="sess-1", depth=2, next_prompt="fix the bug")
    )
    assert set(notif["params"]["payload"].keys()) == {"depth", "next_prompt"}
    assert notif["params"]["payload"] == {"depth": 2, "next_prompt": "fix the bug"}


# -- Dimension 3: Scheduler → EventBus → RPCServer → NDJSON forwarding --------


@pytest.mark.asyncio
async def test_scheduler_to_server_forwards_backlog_changed_notification(
    monkeypatch,
) -> None:
    """A real Scheduler enqueue forwards exactly one backlog_changed notification
    end-to-end. Assert the event channel independently (Pitfall 2 pattern) — the
    enqueue notification fires inside the awaited submit_prompt BEFORE any chat
    response is written."""
    bus = EventBus()
    agent = StubAgent(delay=0.5)
    s = Scheduler(agent, bus)
    await s.start()

    server = RPCServer(MagicMock())
    writes: list = []
    monkeypatch.setattr("backend.rpc.server._write_json", writes.append)
    # Manual subscribe reproduces exactly what server.start() does (no stdin
    # read loop under pytest).
    await bus.subscribe(EVENT_BACKLOG_CHANGED, server._on_event)

    await s.submit_prompt("first")
    await asyncio.sleep(0.05)  # let the first turn start
    await s.submit_prompt("second")

    events = [w for w in writes if w.get("method") == "event"]
    assert len(events) == 1
    assert events[0]["params"]["type"] == "backlog_changed"
    assert events[0]["params"]["payload"] == {"depth": 1, "next_prompt": "second"}
    await s.shutdown()
