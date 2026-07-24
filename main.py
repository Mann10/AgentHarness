from __future__ import annotations

import asyncio
import logging
import sys

from agent import Agent
from config import Config
from context import ConversationContext
from llm import OpenAIClient
from tool import LocalToolProvider, ToolRegistry, register_builtin_tools

logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")
logger = logging.getLogger(__name__)


async def main() -> None:
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    config = Config()
    client = OpenAIClient(config)
    registry = ToolRegistry()
    await registry.load_config(config.mcp_config_path)

    local_provider = LocalToolProvider()
    register_builtin_tools(local_provider)
    registry.add_provider("__builtin__", local_provider)

    context = ConversationContext(
        system_prompt=config.system_prompt,
        count_tokens=client.count_tokens,
        token_limit=config.max_tokens,
        summarize_fn=lambda msgs: client.chat_from_messages(
            [
                {
                    "role": "system",
                    "content": "Summarize the following conversation concisely while preserving key details.",
                },
                *msgs,
            ],
            temperature=0.3,
        ),
    )

    agent = Agent(client, registry, context)
    await agent.start()

    all_tools = registry.list_tools()
    if all_tools:
        tool_cols = 4
        rows = [all_tools[i : i + tool_cols] for i in range(0, len(all_tools), tool_cols)]
        logger.info("Available tools (%d):", len(all_tools))
        for row in rows:
            logger.info("  %s", "  ".join(f"{t.name:<25}" for t in row))
    else:
        logger.warning("No tools available.")

    print("Agent Harness v2 — type 'exit' or 'quit' to stop.\n")

    try:
        while True:
            try:
                user_input = await asyncio.to_thread(input, "> ")
            except (EOFError, KeyboardInterrupt):
                print()
                break
            if user_input.lower() in ("exit", "quit"):
                break
            if not user_input:
                continue

            result = await agent.run(user_input)
            print(result.content)
            if result.forced:
                print(
                    f"\n[Max tool iterations ({result.iterations}) reached. Forced response.]"
                )
            print(f"[{agent.context.total_tokens}/{config.max_tokens} tokens]")
    finally:
        await agent.shutdown()


if __name__ == "__main__":
    asyncio.run(main())
