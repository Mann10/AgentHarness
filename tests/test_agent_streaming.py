from __future__ import annotations

import pytest

from agent.core import Agent
from harness.events import (
    ErrorEvent,
    ResponseComplete,
    ToolCallEvent,
    ToolResultEvent,
    TokenProduced,
)
from llm.base import StreamChunk
from session.models import Session
from tool.models import ToolCall
from tool.registry import ToolRegistry
from unittest.mock import AsyncMock, MagicMock


class StreamingStubLLM:
    """Stub with configurable stream_chat for agent streaming tests."""

    def __init__(self, chunks=(), tool_calls=None, fail_after=None):
        self.chunks = list(chunks)
        self.tool_calls = tool_calls
        self.fail_after = fail_after  # raise RuntimeError after N chunks

    async def stream_chat(self, messages, tools=None, **kwargs):
        for i, chunk in enumerate(self.chunks):
            if self.fail_after is not None and i >= self.fail_after:
                raise RuntimeError("stream failed")
            yield StreamChunk(content=chunk)
        if self.tool_calls is not None and tools:
            yield StreamChunk(tool_calls=self.tool_calls)


def _make_agent(llm, *, max_tool_iterations=1, emit=None):
    registry = MagicMock(spec=ToolRegistry)
    registry.list_tools = MagicMock(return_value=[MagicMock()])
    registry.call_tool = AsyncMock(return_value=MagicMock(content="sunny, 72F"))
    session = Session.create(
        system_prompt="test",
        count_tokens=len,
        token_limit=1000,
    )
    kwargs = {"emit": emit} if emit is not None else {}
    return Agent(llm, registry, session, max_tool_iterations=max_tool_iterations, **kwargs)


async def test_agent_emits_token_produced_per_chunk() -> None:
    """Text chunks each emit TokenProduced; context gets one complete message."""
    llm = StreamingStubLLM(chunks=("Hel", "lo"))
    received = []

    async def collector(event):
        received.append(event)

    agent = _make_agent(llm, emit=collector)
    await agent.run("hi")

    tokens = [e for e in received if isinstance(e, TokenProduced)]
    assert len(tokens) == 2
    assert tokens[0].chunk == "Hel"
    assert tokens[1].chunk == "lo"
    assert all(t.session_id == agent._session.id for t in tokens)

    complete = [e for e in received if isinstance(e, ResponseComplete)]
    assert len(complete) == 1
    assert complete[0].content == "Hello"

    messages = agent._context._messages
    assert len(messages) == 2  # user + one assistant message
    assert messages[1].role == "assistant"
    assert messages[1].content == "Hello"


async def test_agent_tool_turn_emits_no_token_events() -> None:
    """Tool-call turns emit zero TokenProduced; tool flow stays intact."""
    llm = StreamingStubLLM(tool_calls=[
        ToolCall(id="call_1", name="get_weather", arguments={"location": "NYC"}),
    ])
    received = []

    async def collector(event):
        received.append(event)

    agent = _make_agent(llm, emit=collector)
    await agent.run("weather in NYC")

    tokens = [e for e in received if isinstance(e, TokenProduced)]
    assert len(tokens) == 0

    tool_calls = [e for e in received if isinstance(e, ToolCallEvent)]
    tool_results = [e for e in received if isinstance(e, ToolResultEvent)]
    assert len(tool_calls) >= 1
    assert tool_calls[0].tool_name == "get_weather"
    assert len(tool_results) >= 1
    assert "sunny" in tool_results[0].result


async def test_agent_mid_stream_error_keeps_partial_out_of_context() -> None:
    """Mid-stream failure emits ErrorEvent; partial content never persisted (D-05)."""
    llm = StreamingStubLLM(chunks=("Hel", "lo"), fail_after=1)
    received = []

    async def collector(event):
        received.append(event)

    agent = _make_agent(llm, emit=collector)

    with pytest.raises(RuntimeError):
        await agent.run("hi")

    errors = [e for e in received if isinstance(e, ErrorEvent)]
    assert len(errors) == 1
    assert "stream failed" in errors[0].error

    messages = agent._context._messages
    assert len(messages) == 1  # only the user message — no assistant message
    assert messages[0].role == "user"

    complete = [e for e in received if isinstance(e, ResponseComplete)]
    assert len(complete) == 0


async def test_agent_forced_path_streams() -> None:
    """Max-iteration forced call streams text and emits ResponseComplete(forced=True)."""

    class _ForcedStub(StreamingStubLLM):
        async def stream_chat(self, messages, tools=None, **kwargs):
            if tools:
                yield StreamChunk(tool_calls=self.tool_calls)
            else:
                yield StreamChunk(content="Final text")

    llm = _ForcedStub(tool_calls=[
        ToolCall(id="call_1", name="get_weather", arguments={"location": "NYC"}),
    ])
    received = []

    async def collector(event):
        received.append(event)

    agent = _make_agent(llm, emit=collector)
    result = await agent.run("hi")

    tokens = [e for e in received if isinstance(e, TokenProduced)]
    assert len(tokens) >= 1
    assert tokens[0].chunk == "Final text"

    complete = [e for e in received if isinstance(e, ResponseComplete)]
    assert len(complete) == 1
    assert complete[0].forced is True
    assert complete[0].content == "Final text"

    assert result.forced is True
