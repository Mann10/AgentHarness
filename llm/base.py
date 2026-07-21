from abc import ABC, abstractmethod
from collections.abc import Generator

from config import Config
from context.context import ConversationContext


class BaseLLMClient(ABC):
    def __init__(self, config: Config):
        self.config = config

    @abstractmethod
    def chat(self, context: ConversationContext, **kwargs) -> str: ...

    @abstractmethod
    def chat_from_messages(self, messages: list[dict], **kwargs) -> str: ...

    @abstractmethod
    def stream_chat(
        self, context: ConversationContext, **kwargs
    ) -> Generator[str, None, None]: ...

    def count_tokens(self, text: str) -> int:
        try:
            import tiktoken

            encoder = tiktoken.encoding_for_model(self.config.model)
            return len(encoder.encode(text))
        except (ImportError, KeyError):
            return len(text.split())
