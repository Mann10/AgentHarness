from __future__ import annotations

import asyncio

import pytest

from harness.event_bus import EventBus
from harness.events import BacklogChangedEvent
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
