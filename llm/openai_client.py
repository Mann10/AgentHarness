from __future__ import annotations

import json
from collections.abc import Generator

from openai import APIConnectionError, APIError, AsyncOpenAI

from config import Config
from context.context import ConversationContext
from llm.base import BaseLLMClient
from llm.errors import LLMConnectionError, LLMResponseError
from tool.models import LLMResponse, Tool, ToolCall


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
        api_tools = None
        if tools:
            if tools and isinstance(tools[0], Tool):
                api_tools = [
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
            else:
                api_tools = tools

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
        except APIError as e:
            raise LLMResponseError(
                f"API error: {e.status_code} {e.message}"
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
        self, context: ConversationContext, **kwargs
    ) -> Generator[str, None, None]:
        raise NotImplementedError("stream_chat not yet implemented")
