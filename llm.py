from openai import OpenAI

from config import Config


def ask_llm(messages: list[dict], config: Config | None = None) -> str:
    if config is None:
        config = Config()

    client = OpenAI(base_url=config.base_url, api_key=config.api_key)
    response = client.chat.completions.create(
        model=config.model,
        messages=messages,
    )
    return response.choices[0].message.content or ""
