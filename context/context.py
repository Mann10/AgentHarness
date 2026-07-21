from __future__ import annotations

import json
from collections.abc import Awaitable, Callable
from dataclasses import asdict

from context.message import Message
from tool.models import ToolCall


class ConversationContext:
    def __init__(
        self,
        system_prompt: str | None = None,
        *,
        count_tokens: Callable[[str], int],
        token_limit: int,
        summarize_fn: Callable[[list[dict]], Awaitable[str]] | None = None,
        summarize_threshold: float = 0.75,
        keep_recent_exchanges: int = 2,
    ) -> None:
        self._count_tokens = count_tokens
        self.token_limit = token_limit
        self._summarize_fn = summarize_fn
        self._summarize_threshold = summarize_threshold
        self._keep_recent_exchanges = keep_recent_exchanges
        self._messages: list[Message] = []
        self.total_tokens: int = 0

        if system_prompt:
            self._messages.append(Message(role="system", content=system_prompt))
            self.total_tokens += self._count_tokens(system_prompt)

    async def add_message(self, message: Message) -> None:
        if message.token_count == 0:
            message.token_count = self._count_tokens(message.content)
        self._messages.append(message)
        self.total_tokens += message.token_count
        if message.role == "assistant":
            await self._maybe_summarize()

    async def add_user_message(self, content: str) -> None:
        await self.add_message(Message(role="user", content=content))

    async def add_assistant_message(self, content: str) -> None:
        await self.add_message(Message(role="assistant", content=content))

    async def add_assistant_tool_message(self, content: str | None, tool_calls: list[ToolCall]) -> None:
        msg = Message(role="assistant", content=content or "", tool_calls=tool_calls)
        tc_str = json.dumps([asdict(tc) for tc in tool_calls])
        msg.token_count = self._count_tokens((content or "") + tc_str)
        self._messages.append(msg)
        self.total_tokens += msg.token_count
        await self._maybe_summarize()

    async def add_tool_message(self, tool_call_id: str, content: str) -> None:
        msg = Message(role="tool", content=content, tool_call_id=tool_call_id)
        msg.token_count = self._count_tokens(content)
        self._messages.append(msg)
        self.total_tokens += msg.token_count

    def to_llm_messages(self) -> list[dict]:
        result = []
        for m in self._messages:
            d = {"role": m.role, "content": m.content}
            if m.tool_calls:
                d["tool_calls"] = [
                    {
                        "id": tc.id,
                        "type": "function",
                        "function": {"name": tc.name, "arguments": json.dumps(tc.arguments)},
                    }
                    for tc in m.tool_calls
                ]
            if m.tool_call_id:
                d["tool_call_id"] = m.tool_call_id
            result.append(d)
        return result

    async def _maybe_summarize(self) -> None:
        if not self._summarize_fn:
            return
        if self.total_tokens < self.token_limit * self._summarize_threshold:
            return

        system_msgs = [m for m in self._messages if m.role == "system"]
        keep_count = self._keep_recent_exchanges * 2
        recent = self._messages[-keep_count:] if keep_count > 0 else []

        always_keep = []
        if not any(m in recent for m in self._messages if m.role == "user"):
            for m in reversed(self._messages):
                if m.role == "user" and m not in system_msgs:
                    always_keep.append(m)
                    break

        to_summarize = [
            m
            for m in self._messages
            if m not in system_msgs and m not in recent and m not in always_keep
        ]
        if not to_summarize:
            return

        print(
            f"\n--- [CONTEXT] Summarization triggered ({self.total_tokens}/{self.token_limit} tokens) ---"
        )
        print(f"--- [CONTEXT] Summarizing {len(to_summarize)} message(s):")
        for m in to_summarize:
            preview = m.content[:80] + "..." if len(m.content) > 80 else m.content
            print(f"--- [CONTEXT]   [{m.role}] ({m.token_count}t) {preview}")

        try:
            summary_text = await self._summarize_fn(
                [{"role": m.role, "content": m.content} for m in to_summarize]
            )
        except Exception as e:
            print(f"--- [CONTEXT] Summarization failed: {e}")
            return

        summary_msg = Message(
            role="system",
            content=f"Previous conversation summary: {summary_text}",
        )
        summary_msg.token_count = self._count_tokens(summary_msg.content)

        for m in to_summarize:
            self._messages.remove(m)
            self.total_tokens -= m.token_count

        self._messages.insert(len(system_msgs), summary_msg)
        self.total_tokens += summary_msg.token_count

        preview = (
            summary_msg.content[:80] + "..."
            if len(summary_msg.content) > 80
            else summary_msg.content
        )
        print(
            f"--- [CONTEXT] -> Replaced with: [{summary_msg.role}] ({summary_msg.token_count}t) {preview}"
        )
        print(f"--- [CONTEXT] Total tokens now: {self.total_tokens}/{self.token_limit}\n")
