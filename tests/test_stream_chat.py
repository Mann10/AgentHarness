from __future__ import annotations

from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock

import pytest
import httpx
from openai import APIConnectionError, APIStatusError

from config import Config
from llm.base import StreamChunk
from llm.errors import LLMConnectionError, LLMResponseError
from llm.openai_client import OpenAIClient
from tool.models import Tool, ToolCall


def _make_client(stream) -> OpenAIClient:
    client = OpenAIClient(Config(base_url="http://test.local/v1", api_key="test", model="test-model"))
    client._client = MagicMock()
    client._client.chat.completions.create = AsyncMock(return_value=stream)
    return client


def _text_delta(content: str):
    return SimpleNamespace(
        choices=[SimpleNamespace(delta=SimpleNamespace(content=content, tool_calls=None))]
    )


def _tool_delta(index: int, *, call_id: str | None = None, name: str | None = None, args: str | None = None):
    tc = SimpleNamespace(
        index=index, id=call_id,
        function=SimpleNamespace(name=name, arguments=args),
    )
    return SimpleNamespace(
        choices=[SimpleNamespace(delta=SimpleNamespace(content=None, tool_calls=[tc]))]
    )


async def test_stream_chat_yields_text_chunks() -> None:
    """Three content deltas yield one StreamChunk each with tool_calls None."""

    async def stream():
        yield _text_delta("Hel")
        yield _text_delta("lo ")
        yield _text_delta("world")

    client = _make_client(stream())
    chunks = [c async for c in client.stream_chat([{"role": "user", "content": "hi"}])]

    assert [c.content for c in chunks] == ["Hel", "lo ", "world"]
    assert all(c.tool_calls is None for c in chunks)


async def test_stream_chat_assembles_tool_calls() -> None:
    """Fragmented tool deltas assemble into one final chunk with ToolCall list."""

    async def stream():
        yield _tool_delta(0, call_id="call_1", name="get_weather")
        yield _tool_delta(0, args='{"loc')
        yield _tool_delta(0, args='ation":"NYC"}')

    client = _make_client(stream())
    chunks = [c async for c in client.stream_chat([{"role": "user", "content": "hi"}])]

    assert all(not c.content for c in chunks)
    with_tool_calls = [c for c in chunks if c.tool_calls is not None]
    assert len(with_tool_calls) == 1
    assert with_tool_calls[0].tool_calls == [
        ToolCall(id="call_1", name="get_weather", arguments={"location": "NYC"})
    ]


async def test_stream_chat_maps_connection_error() -> None:
    """create() raising APIConnectionError surfaces as LLMConnectionError."""
    client = _make_client(None)
    client._client.chat.completions.create = AsyncMock(
        side_effect=APIConnectionError(request=None)
    )

    with pytest.raises(LLMConnectionError):
        async for _ in client.stream_chat([{"role": "user", "content": "hi"}]):
            pass


async def test_stream_chat_maps_stream_error() -> None:
    """A delta raising APIError mid-iteration surfaces as LLMResponseError."""

    async def stream():
        yield _text_delta("partial")
        request = httpx.Request("POST", "http://test.local/v1/chat/completions")
        response = httpx.Response(500, request=request)
        raise APIStatusError("boom", response=response, body=None)

    client = _make_client(stream())

    with pytest.raises(LLMResponseError):
        async for _ in client.stream_chat([{"role": "user", "content": "hi"}]):
            pass


async def test_stream_chat_passes_tools_to_api() -> None:
    """Tool dataclasses are converted to OpenAI function-schema dicts in create()."""

    async def stream():
        if False:
            yield None

    client = _make_client(stream())
    chunks = [
        c
        async for c in client.stream_chat(
            [{"role": "user", "content": "hi"}],
            tools=[
                Tool(
                    name="get_weather",
                    description="d",
                    input_schema={"type": "object"},
                )
            ],
        )
    ]

    assert chunks == []
    create = client._client.chat.completions.create
    create.assert_awaited_once()
    kwargs = create.call_args.kwargs
    assert kwargs["tools"] == [
        {
            "type": "function",
            "function": {
                "name": "get_weather",
                "description": "d",
                "parameters": {"type": "object"},
            },
        }
    ]
    assert kwargs["stream"] is True
