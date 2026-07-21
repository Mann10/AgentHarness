from collections.abc import Generator

from openai import OpenAI
from openai import APIConnectionError, APIError

from config import Config
from llm.base import BaseLLMClient
from llm.errors import LLMConnectionError, LLMResponseError


class OpenAIClient(BaseLLMClient):
    def __init__(self, config: Config):
        super().__init__(config)
        self._client = OpenAI(
            base_url=config.base_url,
            api_key=config.api_key,
        )

    def chat(self, messages: list[dict], **kwargs) -> str:
        try:
            response = self._client.chat.completions.create(
                model=self.config.model,
                messages=messages,
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

        content = response.choices[0].message.content
        if content is None:
            raise LLMResponseError("Model returned null content")
        return content

    def stream_chat(
        self, messages: list[dict], **kwargs
    ) -> Generator[str, None, None]:
        raise NotImplementedError("stream_chat not yet implemented")
