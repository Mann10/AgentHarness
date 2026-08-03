from __future__ import annotations

import json
from collections.abc import AsyncIterator

from openai import APIConnectionError, APIError, APIStatusError, AsyncOpenAI

from config import Config
from context.context import ConversationContext
from llm.base import BaseLLMClient, StreamChunk
from llm.errors import LLMConnectionError, LLMResponseError
from tool.models import LLMResponse, Tool, ToolCall


def _convert_tools(
    tools: list[Tool] | list[dict] | None,
) -> list[dict] | None:
    """Convert Tool dataclasses to OpenAI function-schema dicts."""
    if not tools:
        return None
    if isinstance(tools[0], Tool):
        return [
            {
                "type": "function",
                "function": {
                    "name": t.name,
                    "description": t.description,
                    "parameters": t.input_schema,
                },
            }
            for t in tools
        ]
    return tools


class OpenAIClient(BaseLLMClient):
    def __init__(self, config: Config):
        super().__init__(config)
        self._client = AsyncOpenAI(
            base_url=config.base_url,
            api_key=config.api_key,
        )

    async def chat(
        self, context: ConversationContext, *, tools: list[Tool] | None = None, **kwargs
    ) -> LLMResponse:
        return await self._call_sdk(context.to_llm_messages(), tools=tools, **kwargs)

    async def chat_from_messages(
        self, messages: list[dict], *, tools: list[dict] | None = None, **kwargs
    ) -> LLMResponse:
        return await self._call_sdk(messages, tools=tools, **kwargs)

    async def _call_sdk(
        self,
        messages: list[dict],
        *,
        tools: list[Tool] | list[dict] | None = None,
        **kwargs,
    ) -> LLMResponse:
        api_tools = _convert_tools(tools)

        try:
            response = await self._client.chat.completions.create(
                model=self.config.model,
                messages=messages,
                tools=api_tools or None,
                tool_choice="auto" if api_tools else None,
                temperature=kwargs.get("temperature", self.config.temperature),
                max_tokens=kwargs.get("max_tokens", self.config.max_tokens),
            )
        except APIConnectionError as e:
            raise LLMConnectionError(
                f"Failed to connect to {self.config.base_url}"
            ) from e
        except APIStatusError as e:
            raise LLMResponseError(
                f"API error: {e.status_code} {e.message}"
            ) from e
        except APIError as e:
            raise LLMResponseError(
                f"API error: {e.message}"
            ) from e

        msg = response.choices[0].message

        if msg.tool_calls:
            return LLMResponse(
                content=msg.content,
                tool_calls=[
                    ToolCall(
                        id=tc.id,
                        name=tc.function.name,
                        arguments=json.loads(tc.function.arguments),
                    )
                    for tc in msg.tool_calls
                ],
            )

        if msg.content is None:
            raise LLMResponseError("Model returned null content")

        return LLMResponse(content=msg.content, tool_calls=None)

    async def stream_chat(
        self,
        messages: list[dict],
        *,
        tools: list[Tool] | list[dict] | None = None,
        **kwargs,
    ) -> AsyncIterator[StreamChunk]:
        """Stream a chat completion (D-01 streaming path).

        Text turns: yields one StreamChunk per content delta (one event
        per SDK delta — no additional client-side batching).
        Tool-call turns: yields zero content chunks, then a single final
        chunk with the assembled ToolCall list. Turn type is decided here
        from the deltas (D-03), never by the caller.
        """
        api_tools = _convert_tools(tools)

        try:
            stream = await self._client.chat.completions.create(
                model=self.config.model,
                messages=messages,
                tools=api_tools or None,
                tool_choice="auto" if api_tools else None,
                temperature=kwargs.get("temperature", self.config.temperature),
                max_tokens=kwargs.get("max_tokens", self.config.max_tokens),
                stream=True,
            )
        except APIConnectionError as e:
            raise LLMConnectionError(
                f"Failed to connect to {self.config.base_url}"
            ) from e
        except APIStatusError as e:
            raise LLMResponseError(
                f"API error: {e.status_code} {e.message}"
            ) from e

        tool_call_parts: dict[int, dict] = {}
        try:
            async for delta in stream:
                if not delta.choices:
                    continue
                choice = delta.choices[0]
                d = choice.delta
                if d.content:
                    yield StreamChunk(content=d.content)
                if d.tool_calls:
                    for tc in d.tool_calls:
                        entry = tool_call_parts.setdefault(
                            tc.index, {"id": "", "name": "", "arguments": ""}
                        )
                        if tc.id:
                            entry["id"] = tc.id
                        if tc.function and tc.function.name:
                            entry["name"] = tc.function.name
                        if tc.function and tc.function.arguments:
                            entry["arguments"] += tc.function.arguments
        except APIConnectionError as e:
            raise LLMConnectionError(
                f"Stream connection lost to {self.config.base_url}"
            ) from e
        except APIStatusError as e:
            raise LLMResponseError(
                f"API error during stream: {e.status_code} {e.message}"
            ) from e
        except APIError as e:
            raise LLMResponseError(
                f"API error during stream: {e.message}"
            ) from e

        if tool_call_parts:
            calls = [
                ToolCall(
                    id=parts["id"],
                    name=parts["name"],
                    arguments=json.loads(parts["arguments"]) if parts["arguments"] else {},
                )
                for _, parts in sorted(tool_call_parts.items())
            ]
            yield StreamChunk(tool_calls=calls)
