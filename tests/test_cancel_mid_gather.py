from __future__ import annotations

import asyncio
from unittest.mock import AsyncMock, MagicMock

import pytest

from agent.core import Agent
from llm.base import StreamChunk
from session.models import Session
from tool.models import Tool, ToolCall, ToolResult
from tool.registry import ToolRegistry


class BlockingRegistry:
    """A minimal registry whose call_tool blocks until released (D-14).

    Mirrors the ToolRegistry surface Agent uses: list_tools, call_tool, start.
    start() is a no-op so Agent.start() works without a real provider stack.
    """

    def __init__(self, started: asyncio.Event, release: asyncio.Event) -> None:
        self._started = started
        self._release = release
        self.calls: list[tuple[str, dict]] = []

    async def start(self) -> None:
        pass

    async def shutdown(self) -> None:
        pass

    def list_tools(self) -> list[Tool]:
        return [Tool(name="get_weather", description="weather lookup")]

    async def call_tool(self, name: str, arguments: dict) -> ToolResult:
        self.calls.append((name, arguments))
        self._started.set()
        await self._release.wait()
        return ToolResult(tool_call_id=name, content="sunny, 72F")


class ToolThenTextLLM:
    """Stub LLM: first response carries tool_calls, every later one is text.

    Matches the StreamingStubLLM pattern from test_agent_streaming.py.
    """

    def __init__(self, tool_calls):
        self.tool_calls = tool_calls
        self.calls = 0

    async def stream_chat(self, messages, tools=None, **kwargs):
        if self.calls == 0:
            self.calls += 1
            yield StreamChunk(tool_calls=self.tool_calls)
        else:
            self.calls += 1
            yield StreamChunk(content="final text reply")


def _assert_no_dangling_tool_calls(messages: list[dict]) -> None:
    """Provider-valid alternation: every assistant msg with tool_calls has a
    following tool msg (D-14)."""
    for i, m in enumerate(messages):
        if m.get("tool_calls"):
            assert i + 1 < len(messages), (
                f"assistant tool_calls at index {i} has no following message"
            )
            assert messages[i + 1]["role"] == "tool", (
                f"assistant tool_calls at index {i} is not followed by a tool result"
            )


def _make_agent(llm, registry, *, max_tool_iterations=5) -> Agent:
    session = Session.create(
        system_prompt="test",
        count_tokens=len,
        token_limit=1000,
    )
    return Agent(llm, registry, session, max_tool_iterations=max_tool_iterations)


async def test_cancel_mid_gather() -> None:
    """D-14 regression: cancelling during the tool-result gather must not leave
    an orphaned assistant tool_calls message in context.

    The assistant tool_calls message is committed BEFORE the gather
    (agent/core.py L148), so a cancel mid-gather orphans it. After the fix,
    to_llm_messages() must have provider-valid alternation.
    """
    started = asyncio.Event()
    release = asyncio.Event()
    registry = BlockingRegistry(started, release)
    llm = ToolThenTextLLM(tool_calls=[
        ToolCall(id="call_1", name="get_weather", arguments={"location": "NYC"}),
    ])
    agent = _make_agent(llm, registry)

    task = asyncio.create_task(agent.run("hi"))
    await asyncio.wait_for(started.wait(), timeout=2)
    task.cancel()
    with pytest.raises(asyncio.CancelledError):
        await task

    msgs = agent.context.to_llm_messages()
    _assert_no_dangling_tool_calls(msgs)


async def test_next_turn_streams_after_cancel() -> None:
    """D-14: after a mid-gather cancel, a second run() streams a text response
    cleanly — no provider-validation error from dangling tool_calls."""
    started = asyncio.Event()
    release = asyncio.Event()
    registry = BlockingRegistry(started, release)
    llm = ToolThenTextLLM(tool_calls=[
        ToolCall(id="call_1", name="get_weather", arguments={"location": "NYC"}),
    ])
    agent = _make_agent(llm, registry)

    task = asyncio.create_task(agent.run("hi"))
    await asyncio.wait_for(started.wait(), timeout=2)
    task.cancel()
    with pytest.raises(asyncio.CancelledError):
        await task

    # Second turn: the stub now returns text — must complete without raising
    # and the streamed message list must be provider-valid.
    result = await agent.run("continue")
    assert result.content == "final text reply"
    _assert_no_dangling_tool_calls(agent.context.to_llm_messages())


async def test_normal_round_trip_unaffected() -> None:
    """D-14: without cancellation, a full tool-call round-trip completes
    normally (assistant tool_calls + tool result both present)."""
    started = asyncio.Event()
    release = asyncio.Event()
    registry = BlockingRegistry(started, release)
    llm = ToolThenTextLLM(tool_calls=[
        ToolCall(id="call_1", name="get_weather", arguments={"location": "NYC"}),
    ])
    agent = _make_agent(llm, registry)

    # Release immediately — no cancel; the round-trip runs to completion.
    release.set()
    result = await agent.run("hi")
    assert result.content == "final text reply"

    msgs = agent.context.to_llm_messages()
    roles = [m["role"] for m in msgs]
    assert "assistant" in roles
    assert "tool" in roles
    # The tool_calls round-trip completed: no dangling calls, results present.
    _assert_no_dangling_tool_calls(msgs)
    assert any(m.get("tool_calls") for m in msgs)
