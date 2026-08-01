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


@pytest.fixture
def runtime_with_store():
    """RuntimeAPI with an isolated tempdir JSONLSessionStore."""
    import tempfile
    from session.store import JSONLSessionStore
    config = MagicMock()
    config.system_prompt = "test"
    config.max_tokens = 1000
    config.max_tool_iterations = 5
    client = MagicMock()
    client.count_tokens = len
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
    store = JSONLSessionStore(tempfile.mkdtemp())
    return RuntimeAPI(config, client, registry, store=store, backlog_maxsize=5)


@pytest.mark.asyncio
async def test_switch_session_restores_context(runtime_with_store: RuntimeAPI) -> None:
    """switch_session on a persisted session restores context (D-10 path)."""
    runtime = runtime_with_store
    await runtime.start()
    first_id = runtime.active_session.id
    await runtime.active_session.context.add_user_message("hello")
    await runtime._session_manager.save_session()
    second = await runtime.create_session()  # switches active away
    assert second.id != first_id
    success = await runtime.switch_session(first_id)
    assert success is True
    assert runtime.active_session.id == first_id
    msgs = runtime.active_session.context.to_llm_messages()
    assert any(m["role"] == "user" and m["content"] == "hello" for m in msgs)
    await runtime.shutdown()


@pytest.mark.asyncio
async def test_switch_session_missing_id_returns_false(runtime_with_store: RuntimeAPI) -> None:
    runtime = runtime_with_store
    await runtime.start()
    assert await runtime.switch_session("nonexistent-id") is False
    await runtime.shutdown()


@pytest.mark.asyncio
async def test_get_session_history_returns_chronological_messages(runtime_with_store: RuntimeAPI) -> None:
    runtime = runtime_with_store
    await runtime.start()
    sid = runtime.active_session.id
    await runtime.active_session.context.add_user_message("first")
    await runtime.active_session.context.add_assistant_message("second")
    await runtime._session_manager.save_session()
    history = await runtime.get_session_history(sid)
    assert history is not None
    roles = [m["role"] for m in history]
    assert roles == ["user", "assistant"]
    assert history[0]["content"] == "first"
    assert history[1]["content"] == "second"
    assert await runtime.get_session_history("missing") is None
    await runtime.shutdown()


@pytest.mark.asyncio
async def test_submit_prompt_auto_titles_new_session(runtime_with_store: RuntimeAPI) -> None:
    """D-13: first prompt becomes the title, first line truncated to 15 chars + '...'."""
    runtime = runtime_with_store
    await runtime.start()
    long_prompt = "x" * 60
    await runtime.submit_prompt(long_prompt)
    assert runtime.active_session.title == ("x" * 15) + "..."
    await runtime.shutdown()


@pytest.mark.asyncio
async def test_submit_prompt_title_uses_first_line(runtime_with_store: RuntimeAPI) -> None:
    """Title derives from the first line of the prompt, not the whole text."""
    runtime = runtime_with_store
    await runtime.start()
    await runtime.submit_prompt("multi-line first prompt\nsecond line here")
    assert runtime.active_session.title == "multi-line firs..."
    await runtime.shutdown()


@pytest.mark.asyncio
async def test_submit_prompt_title_persists_to_store(runtime_with_store: RuntimeAPI) -> None:
    """Auto-title reaches disk so list_sessions returns a real name, not None."""
    runtime = runtime_with_store
    await runtime.start()
    sid = runtime.active_session.id
    await runtime.submit_prompt("a persistent title question")
    await asyncio.sleep(0.3)
    summaries = await runtime.list_sessions()
    matches = [s for s in summaries if s.id == sid]
    assert len(matches) == 1
    assert matches[0].title == "a persistent ti..."
    await runtime.shutdown()


@pytest.mark.asyncio
async def test_messages_persist_after_each_turn(runtime_with_store: RuntimeAPI) -> None:
    """History is available from the store mid-run, before shutdown."""
    runtime = runtime_with_store
    await runtime.start()
    sid = runtime.active_session.id
    await runtime.submit_prompt("first question")
    await asyncio.sleep(0.3)
    history = await runtime.get_session_history(sid)
    assert history is not None
    roles = [m["role"] for m in history]
    assert "user" in roles
    await runtime.shutdown()


@pytest.mark.asyncio
async def test_scheduler_agent_tracks_active_session_after_create(runtime_with_store: RuntimeAPI) -> None:
    """After create_session, new prompts run against the new session's agent."""
    runtime = runtime_with_store
    await runtime.start()
    first_id = runtime.active_session.id
    await runtime.create_session()  # new session becomes active
    assert runtime.active_session.id != first_id
    assert runtime._scheduler._agent._session.id == runtime.active_session.id
    await runtime.submit_prompt("question for second session")
    await asyncio.sleep(0.3)
    assert runtime._scheduler._agent._session.id == runtime.active_session.id
    await runtime.shutdown()
