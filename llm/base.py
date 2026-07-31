from abc import ABC, abstractmethod
from collections.abc import AsyncIterator
from dataclasses import dataclass

from config import Config
from context.context import ConversationContext
from tool.models import LLMResponse, Tool, ToolCall


@dataclass
class StreamChunk:
    """One streamed delta from the LLM (D-03 contract).

    - Text turns: each chunk carries the next text delta in `content`;
      `tool_calls` is None. The caller accumulates content.
    - Tool-call turns: `content` stays empty; exactly one final chunk
      carries the fully-assembled `tool_calls` list.
    The client decides the turn type by inspecting stream deltas —
    the caller never pre-decides (D-03).
    """

    content: str = ""
    tool_calls: list[ToolCall] | None = None


class BaseLLMClient(ABC):
    def __init__(self, config: Config):
        self.config = config

    @abstractmethod
    async def chat(
        self, context: ConversationContext, *, tools: list[Tool] | None = None, **kwargs
    ) -> LLMResponse: ...

    @abstractmethod
    async def chat_from_messages(
        self, messages: list[dict], *, tools: list[Tool] | list[dict] | None = None, **kwargs
    ) -> LLMResponse: ...

    @abstractmethod
    def stream_chat(
        self,
        messages: list[dict],
        *,
        tools: list[Tool] | list[dict] | None = None,
        **kwargs,
    ) -> AsyncIterator[StreamChunk]: ...

    def count_tokens(self, text: str) -> int:
        try:
            import tiktoken

            encoder = tiktoken.encoding_for_model(self.config.model)
            return len(encoder.encode(text))
        except (ImportError, KeyError):
            return len(text.split())
