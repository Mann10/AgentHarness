from __future__ import annotations

import asyncio
import logging

from agent.result import AgentResult
from context.context import ConversationContext
from llm.base import BaseLLMClient
from tool.registry import ToolRegistry

logger = logging.getLogger(__name__)


class Agent:
    def __init__(
        self,
        llm_client: BaseLLMClient,
        tool_registry: ToolRegistry,
        context: ConversationContext,
        *,
        max_tool_iterations: int = 15,
    ):
        self._llm = llm_client
        self._registry = tool_registry
        self._context = context
        self._max_iterations = max_tool_iterations

    async def start(self) -> None:
        await self._registry.start()

    async def shutdown(self) -> None:
        await self._registry.shutdown()

    @property
    def context(self) -> ConversationContext:
        return self._context

    async def run(self, user_input: str) -> AgentResult:
        await self._context.add_user_message(user_input)

        iterations = 0
        total_tool_calls = 0

        while iterations < self._max_iterations:
            iterations += 1
            tools = self._registry.list_tools()
            logger.info(
                "LLM call #%d with %d tool(s) defined", iterations, len(tools)
            )

            response = await self._llm.chat(
                self._context, tools=tools if tools else None
            )

            if not response.tool_calls:
                logger.info(
                    "LLM call #%d -> text response (%d chars)",
                    iterations,
                    len(response.content or ""),
                )
                await self._context.add_assistant_message(response.content)
                return AgentResult(
                    content=response.content,
                    iterations=iterations,
                    tool_calls_made=total_tool_calls,
                )

            called = ", ".join(
                f"{tc.name}({_arg_summary(tc.arguments)})"
                for tc in response.tool_calls
            )
            logger.info(
                "LLM call #%d -> %d tool call(s): %s",
                iterations,
                len(response.tool_calls),
                called,
            )

            await self._context.add_assistant_tool_message(
                response.content, response.tool_calls
            )

            tasks = [
                self._registry.call_tool(tc.name, tc.arguments)
                for tc in response.tool_calls
            ]
            results = await asyncio.gather(*tasks, return_exceptions=True)

            for tc, result in zip(response.tool_calls, results):
                content = (
                    f"Error: {result}"
                    if isinstance(result, Exception)
                    else result.content
                )
                await self._context.add_tool_message(tc.id, content)

            total_tool_calls += len(response.tool_calls)

        logger.info(
            "Max tool iterations (%d) reached. Forcing text response.",
            self._max_iterations,
        )
        response = await self._llm.chat(self._context)
        await self._context.add_assistant_message(response.content)
        return AgentResult(
            content=response.content,
            iterations=iterations,
            tool_calls_made=total_tool_calls,
            forced=True,
        )


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