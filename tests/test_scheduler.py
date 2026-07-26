from __future__ import annotations

import asyncio

import pytest

from harness.event_bus import EventBus
from harness.events import (
    CancelledEvent,
    ErrorEvent,
    ResponseComplete,
    ToolCallEvent,
    ToolResultEvent,
    TurnStarted,
)
from harness.scheduler import Scheduler
from tests.conftest import StubAgent


@pytest.fixture
async def bus() -> EventBus:
    return EventBus()


@pytest.fixture
async def scheduler(bus: EventBus) -> Scheduler:
    agent = StubAgent(delay=0.1)
    s = Scheduler(agent, bus)
    await s.start()
    return s


@pytest.mark.asyncio
async def test_submit_prompt_starts_turn(scheduler: Scheduler) -> None:
    """submitting a prompt starts agent.run() when idle (D-15 non-blocking)."""
    await scheduler.submit_prompt("hello")
    # Give the task a moment to start
    await asyncio.sleep(0.05)
    assert scheduler.is_busy


@pytest.mark.asyncio
async def test_submit_prompt_returns_immediately() -> None:
    """submit_prompt() returns before agent completes (D-15)."""
    slow_agent = StubAgent(delay=1.0)
    slow_sched = Scheduler(slow_agent, EventBus())
    await slow_sched.start()

    t0 = asyncio.get_event_loop().time()
    await slow_sched.submit_prompt("slow")
    elapsed = asyncio.get_event_loop().time() - t0

    assert elapsed < 0.5, (
        f"submit_prompt should return immediately, took {elapsed:.2f}s"
    )
    await slow_sched.shutdown()


@pytest.mark.asyncio
async def test_backlog_queues_when_busy() -> None:
    """submitting while busy queues to backlog (D-11)."""
    slow_agent = StubAgent(delay=0.5)
    slow_sched = Scheduler(slow_agent, EventBus())
    await slow_sched.start()

    await slow_sched.submit_prompt("first")
    await asyncio.sleep(0.05)  # let it start
    await slow_sched.submit_prompt("second")
    await slow_sched.submit_prompt("third")

    assert slow_sched.backlog_size == 2
    await slow_sched.shutdown()


@pytest.mark.asyncio
async def test_backlog_drains_after_turn() -> None:
    """after a turn completes, the backlog is drained FIFO."""
    agent = StubAgent(delay=0.1)
    s = Scheduler(agent, EventBus())
    await s.start()

    await s.submit_prompt("first")
    await asyncio.sleep(0.05)
    await s.submit_prompt("second")
    await s.submit_prompt("third")

    # Wait for all turns to complete (3 * 0.1s + overhead)
    await asyncio.sleep(1.0)

    assert agent.run_count == 3
    assert agent.last_input == "third"  # FIFO: last processed is "third"
    await s.shutdown()


@pytest.mark.asyncio
async def test_cancel_stops_current_turn() -> None:
    """cancel() stops the currently executing turn."""
    bus = EventBus()
    received = []

    async def collector(e):
        received.append(e)

    await bus.subscribe("CancelledEvent", collector)

    agent = StubAgent(delay=1.0)
    s = Scheduler(agent, bus)
    await s.start()

    await s.submit_prompt("long task")
    await asyncio.sleep(0.05)  # let it start

    await s.cancel()
    await asyncio.sleep(0.2)

    assert not s.is_busy
    assert len(received) == 1
    assert isinstance(received[0], CancelledEvent)
    await s.shutdown()


@pytest.mark.asyncio
async def test_one_turn_at_a_time() -> None:
    """Scheduler never runs two turns concurrently (D-09)."""
    bus = EventBus()
    agent = StubAgent(delay=0.3)
    s = Scheduler(agent, bus)
    await s.start()

    await s.submit_prompt("first")
    await asyncio.sleep(0.05)
    await s.submit_prompt("second")
    await s.submit_prompt("third")

    # At this point only first turn should be running
    assert s.is_busy
    assert s.backlog_size == 2

    await asyncio.sleep(0.5)  # first completes (~0.3s), second starts

    # After first completes, backlog drops by one
    assert agent.run_count == 2  # first completed, second started
    assert s.backlog_size == 1

    await s.shutdown()


@pytest.mark.asyncio
async def test_rejects_submit_when_not_running() -> None:
    """submit_prompt before start() is rejected."""
    agent = StubAgent()
    s = Scheduler(agent, EventBus())
    # Not started
    await s.submit_prompt("hello")
    assert not s.is_busy
    assert s.backlog_size == 0
