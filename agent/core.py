from __future__ import annotations

import asyncio
import logging

from collections.abc import Awaitable, Callable
from typing import Any

from agent.result import AgentResult
from context.context import ConversationContext
from harness.events import (
    ErrorEvent,
    ResponseComplete,
    TokenProduced,
    ToolCallEvent,
    ToolResultEvent,
    TurnStarted,
)
from llm.base import BaseLLMClient
from session.models import Session
from tool.models import LLMResponse, ToolCall
from tool.registry import ToolRegistry

logger = logging.getLogger(__name__)


async def _noop_awaitable() -> None:
    """No-op awaitable used as default emit callback."""
    pass


class Agent:
    def __init__(
        self,
        llm_client: BaseLLMClient,
        tool_registry: ToolRegistry,
        session: Session,
        *,
        max_tool_iterations: int = 15,
        emit: Callable[[Any], Awaitable[None]] | None = None,
    ):
        self._llm = llm_client
        self._registry = tool_registry
        self._session = session
        self._context = session.context
        self._max_iterations = max_tool_iterations
        self._emit = emit or (lambda _: _noop_awaitable())

    async def start(self) -> None:
        await self._registry.start()

    async def shutdown(self) -> None:
        await self._registry.shutdown()

    @property
    def context(self) -> ConversationContext:
        return self._context

    def switch_session(self, session: Session) -> None:
        self._session = session
        self._context = session.context

    async def _stream_llm_call(
        self,
        messages: list[dict],
        *,
        tools: list | None = None,
    ) -> LLMResponse:
        """Run one LLM call through the streaming path (D-01).

        Emits TokenProduced for each text chunk (D-02 — tool-call turns
        produce no token events; their content is null anyway). Turn type
        is decided by the client inspecting deltas (D-03), never here.
        Partial content is never persisted here — the caller only adds a
        complete assistant message after the full response (D-05).
        """
        content_parts: list[str] = []
        tool_calls: list[ToolCall] | None = None
        async for chunk in self._llm.stream_chat(
            messages, tools=tools if tools else None
        ):
            if chunk.content:
                await self._emit(TokenProduced(
                    session_id=self._session.id,
                    chunk=chunk.content,
                ))
                content_parts.append(chunk.content)
            if chunk.tool_calls is not None:
                tool_calls = chunk.tool_calls
        content = "".join(content_parts)
        if tool_calls is not None:
            return LLMResponse(content=None, tool_calls=tool_calls)
        return LLMResponse(content=content, tool_calls=None)

    async def run(self, user_input: str) -> AgentResult:
        await self._context.add_user_message(user_input)
        await self._emit(TurnStarted(
            session_id=self._session.id,
            prompt=user_input,
        ))

        try:
            iterations = 0
            total_tool_calls = 0

            while iterations < self._max_iterations:
                iterations += 1
                tools = self._registry.list_tools()
                logger.info(
                    "LLM call #%d with %d tool(s) defined", iterations, len(tools)
                )

                response = await self._stream_llm_call(
                    self._session.to_llm_messages(),
                    tools=tools if tools else None,
                )

                if not response.tool_calls:
                    logger.info(
                        "LLM call #%d -> text response (%d chars)",
                        iterations,
                        len(response.content or ""),
                    )
                    await self._context.add_assistant_message(response.content)
                    await self._emit(ResponseComplete(
                        session_id=self._session.id,
                        content=response.content,
                        iterations=iterations,
                        tool_calls_made=total_tool_calls,
                    ))
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

                # D-14 baseline: message count BEFORE committing the assistant
                # tool_calls message — any cancel mid-gather rolls back
                # everything from here (the orphaned tool_calls + partial tool
                # results) so the next turn has provider-valid alternation.
                msgs_before_gather = len(self._context._messages)

                await self._context.add_assistant_tool_message(
                    response.content, response.tool_calls
                )

                # Emit tool_call for each tool the LLM wants to call
                for tc in response.tool_calls:
                    await self._emit(ToolCallEvent(
                        session_id=self._session.id,
                        tool_name=tc.name,
                        arguments=tc.arguments,
                    ))

                tasks = [
                    self._registry.call_tool(tc.name, tc.arguments)
                    for tc in response.tool_calls
                ]
                try:
                    results = await asyncio.gather(*tasks, return_exceptions=True)

                    for tc, result in zip(response.tool_calls, results):
                        content = (
                            f"Error: {result}"
                            if isinstance(result, Exception)
                            else result.content
                        )
                        await self._context.add_tool_message(tc.id, content)
                        await self._emit(ToolResultEvent(
                            session_id=self._session.id,
                            tool_name=tc.name,
                            result=content,
                        ))
                except asyncio.CancelledError:
                    # D-14: cancel mid-gather — drop the orphaned assistant
                    # tool_calls message and any partial tool messages so the
                    # next turn has valid alternation (no dangling tool_calls).
                    # total_tokens must stay consistent with _messages.
                    del self._context._messages[msgs_before_gather:]
                    self._context.total_tokens = sum(
                        m.token_count for m in self._context._messages)
                    raise

                total_tool_calls += len(response.tool_calls)

            logger.info(
                "Max tool iterations (%d) reached. Forcing text response.",
                self._max_iterations,
            )
            response = await self._stream_llm_call(
                self._session.to_llm_messages()
            )
            await self._context.add_assistant_message(response.content)
            await self._emit(ResponseComplete(
                session_id=self._session.id,
                content=response.content,
                iterations=iterations,
                tool_calls_made=total_tool_calls,
                forced=True,
            ))
            return AgentResult(
                content=response.content,
                iterations=iterations,
                tool_calls_made=total_tool_calls,
                forced=True,
            )
        except Exception as e:
            await self._emit(ErrorEvent(
                session_id=self._session.id,
                error=str(e),
            ))
            raise


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