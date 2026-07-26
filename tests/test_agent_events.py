from __future__ import annotations

import pytest

from agent.core import Agent
from harness.events import (
    ResponseComplete,
    ToolCallEvent,
    ToolResultEvent,
    TurnStarted,
)


@pytest.mark.asyncio
async def test_agent_accepts_emit_callback() -> None:
    """Agent.__init__ accepts emit kwarg without error (backward compat)."""
    agent = _make_stub_agent()
    assert hasattr(agent, "_emit")


@pytest.mark.asyncio
async def test_agent_works_without_emit() -> None:
    """Existing callers that don't pass emit still work (D-03 backward compat)."""
    agent = _make_stub_agent()
    result = await agent.run("hello")
    assert result.content is not None


@pytest.mark.asyncio
async def test_agent_emits_turn_started() -> None:
    """Agent.run() emits TurnStarted with the correct prompt."""
    received = []

    async def collector(event):
        received.append(event)

    agent = _make_stub_agent(emit=collector)
    await agent.run("test prompt")

    assert len(received) >= 1
    ts = received[0]
    assert isinstance(ts, TurnStarted)
    assert ts.prompt == "test prompt"


@pytest.mark.asyncio
async def test_agent_emits_response_complete_on_text() -> None:
    """Agent.run() emits ResponseComplete when LLM returns text (no tool calls)."""
    received = []

    async def collector(event):
        received.append(event)

    agent = _make_stub_agent(emit=collector, no_tools=True)
    await agent.run("hello")

    complete = [e for e in received if isinstance(e, ResponseComplete)]
    assert len(complete) >= 1
    assert complete[0].content is not None


@pytest.mark.asyncio
async def test_agent_emits_tool_events() -> None:
    """Agent.run() emits ToolCallEvent and ToolResultEvent when tools are called."""
    received = []

    async def collector(event):
        received.append(event)

    agent = _make_stub_agent(emit=collector, no_tools=False)
    await agent.run("weather in NYC")

    tool_calls = [e for e in received if isinstance(e, ToolCallEvent)]
    tool_results = [e for e in received if isinstance(e, ToolResultEvent)]
    assert len(tool_calls) >= 1
    assert len(tool_results) >= 1
    assert tool_calls[0].tool_name == "get_weather"
    assert "sunny" in tool_results[0].result


def _make_stub_agent(emit=None, no_tools=False):
    """Create a minimal Agent with stub dependencies for testing.

    Uses a mock LLM that returns simple text and a minimal tool registry.
    """
    from unittest.mock import AsyncMock, MagicMock

    from llm.base import BaseLLMClient
    from llm.base import LLMResponse
    from session.models import Session
    from tool.models import ToolCall
    from tool.registry import ToolRegistry

    llm = MagicMock(spec=BaseLLMClient)

    if no_tools:
        llm.chat_from_messages = AsyncMock(return_value=LLMResponse(
            content="Hello!",
            tool_calls=None,
        ))
    else:
        llm.chat_from_messages = AsyncMock(return_value=LLMResponse(
            content="",
            tool_calls=[
                ToolCall(id="call_1", name="get_weather", arguments={"location": "NYC"}),
            ],
        ))

    registry = MagicMock(spec=ToolRegistry)
    registry.list_tools = MagicMock(return_value=[MagicMock()])
    registry.call_tool = AsyncMock(return_value=MagicMock(content="sunny, 72F"))

    session = Session.create(
        system_prompt="test",
        count_tokens=len,
        token_limit=1000,
    )

    kwargs = {"emit": emit} if emit is not None else {}
    return Agent(llm, registry, session, max_tool_iterations=1, **kwargs)
