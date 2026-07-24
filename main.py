from __future__ import annotations

import asyncio
import logging
import sys

from config import Config
from context import ConversationContext
from llm import OpenAIClient
from tool import LocalToolProvider, ToolRegistry, register_builtin_tools

logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")
logger = logging.getLogger(__name__)

MAX_TOOL_ITERATIONS = 15


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

    await registry.start()

    all_tools = registry.list_tools()
    if all_tools:
        tool_cols = 4
        rows = [all_tools[i:i+tool_cols] for i in range(0, len(all_tools), tool_cols)]
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

            await context.add_user_message(user_input)

            tool_iterations = 0
            while tool_iterations < MAX_TOOL_ITERATIONS:
                tool_iterations += 1
                tools = registry.list_tools()
                logger.info(
                    "LLM call #%d with %d tool(s) defined",
                    tool_iterations, len(tools),
                )
                response = await client.chat(
                    context, tools=tools if tools else None
                )

                if not response.tool_calls:
                    logger.info(
                        "LLM call #%d → text response (%d chars)",
                        tool_iterations, len(response.content or ""),
                    )
                    await context.add_assistant_message(response.content)
                    print(response.content)
                    print(f"[{context.total_tokens}/{config.max_tokens} tokens]")
                    break

                called = ", ".join(f"{tc.name}({_arg_summary(tc.arguments)})" for tc in response.tool_calls)
                logger.info(
                    "LLM call #%d → %d tool call(s): %s",
                    tool_iterations, len(response.tool_calls), called,
                )

                await context.add_assistant_tool_message(
                    response.content, response.tool_calls
                )

                tasks = [
                    registry.call_tool(tc.name, tc.arguments)
                    for tc in response.tool_calls
                ]
                results = await asyncio.gather(*tasks, return_exceptions=True)

                for tc, result in zip(response.tool_calls, results):
                    if isinstance(result, Exception):
                        content = f"Error: {result}"
                    else:
                        content = result.content
                    await context.add_tool_message(tc.id, content)

            else:
                print(
                    f"\n[Max tool iterations ({MAX_TOOL_ITERATIONS}) reached. Forcing response.]"
                )
                response = await client.chat(context)
                await context.add_assistant_message(response.content)
                print(response.content)
                print(f"[{context.total_tokens}/{config.max_tokens} tokens]")
    finally:
        await registry.shutdown()


def _arg_summary(arguments: dict) -> str:
    parts = []
    for k, v in arguments.items():
        s = str(v)
        if len(s) > 60:
            s = s[:57] + "..."
        if isinstance(v, str) and "\n" in v:
            s = s[:40] + "..."
        parts.append(f"{k}={s}")
    return ", ".join(parts) if parts else "(no args)"


if __name__ == "__main__":
    asyncio.run(main())
