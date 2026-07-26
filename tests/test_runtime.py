from __future__ import annotations

import asyncio
from unittest.mock import AsyncMock, MagicMock

import pytest

from agent import Agent
from harness import (
    CancellationToken,
    EventBus,
    RuntimeAPI,
    Scheduler,
    SessionManager,
)


@pytest.fixture
def runtime():
    """Create a RuntimeAPI with mock dependencies."""
    config = MagicMock()
    config.system_prompt = "test"
    config.max_tokens = 1000
    config.max_tool_iterations = 5

    client = MagicMock()
    client.count_tokens = len
    # Make chat_from_messages return a response with no tool calls (text only)
    async def _mock_chat_from_messages(messages, **kwargs):
        response = MagicMock()
        response.tool_calls = None
        response.content = "mock response"
        return response

    client.chat_from_messages = _mock_chat_from_messages

    registry = MagicMock()
    registry.list_tools = MagicMock(return_value=[])
    registry.start = AsyncMock()
    registry.shutdown = AsyncMock()

    return RuntimeAPI(config, client, registry, backlog_maxsize=5)


@pytest.mark.asyncio
async def test_runtime_api_has_4_methods(runtime: RuntimeAPI) -> None:
    """RuntimeAPI exposes the 4 API methods (D-13)."""
    assert hasattr(runtime, "submit_prompt")
    assert hasattr(runtime, "cancel")
    assert hasattr(runtime, "list_sessions")
    assert hasattr(runtime, "switch_session")


@pytest.mark.asyncio
async def test_runtime_start_creates_session_and_agent(runtime: RuntimeAPI) -> None:
    """start() creates a default session and agent."""
    await runtime.start()

    assert runtime.active_session is not None
    assert runtime.event_bus is not None
    assert runtime.is_busy is not None  # property exists

    await runtime.shutdown()


@pytest.mark.asyncio
async def test_runtime_submit_prompt_works_after_start(runtime: RuntimeAPI) -> None:
    """submit_prompt() works after Runtime is started."""
    await runtime.start()
    # This should not raise -- delegates to Scheduler
    await runtime.submit_prompt("hello")
    # Give the scheduler a moment
    await asyncio.sleep(0.1)
    await runtime.shutdown()


@pytest.mark.asyncio
async def test_runtime_cancel_does_not_raise(runtime: RuntimeAPI) -> None:
    """cancel() is safe to call even when no turn is running."""
    runtime.cancel()  # Should not raise

    await runtime.start()
    runtime.cancel()  # Should not raise after start either
    await runtime.shutdown()


@pytest.mark.asyncio
async def test_runtime_shutdown_saves_session(runtime: RuntimeAPI) -> None:
    """shutdown() persists the active session."""
    await runtime.start()
    session_id = runtime.active_session.id
    await runtime.shutdown()

    # Session should still be listable after shutdown
    sessions = await runtime.list_sessions()
    ids = [s.id for s in sessions]
    assert session_id in ids


@pytest.mark.asyncio
async def test_runtime_event_bus_property(runtime: RuntimeAPI) -> None:
    """event_bus property returns an EventBus instance (D-14)."""
    bus = runtime.event_bus
    assert isinstance(bus, EventBus)


@pytest.mark.asyncio
async def test_runtime_submit_prompt_no_start_does_not_raise(runtime: RuntimeAPI) -> None:
    """submit_prompt() before start() logs warning but doesn't raise."""
    await runtime.submit_prompt("hello")  # Should not raise
