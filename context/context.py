from collections.abc import Callable
from context.message import Message


class ConversationContext:
    def __init__(
        self,
        system_prompt: str | None = None,
        *,
        count_tokens: Callable[[str], int],
        token_limit: int,
        summarize_fn: Callable[[list[dict]], str] | None = None,
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
            self.add_message(Message(role="system", content=system_prompt))

    def add_message(self, message: Message) -> None:
        if message.token_count == 0:
            message.token_count = self._count_tokens(message.content)
        self._messages.append(message)
        self.total_tokens += message.token_count
        if message.role == "assistant":
            self._maybe_summarize()

    def add_user_message(self, content: str) -> None:
        self.add_message(Message(role="user", content=content))

    def add_assistant_message(self, content: str) -> None:
        self.add_message(Message(role="assistant", content=content))

    def to_llm_messages(self) -> list[dict]:
        return [{"role": m.role, "content": m.content} for m in self._messages]

    def _maybe_summarize(self) -> None:
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
            m for m in self._messages
            if m not in system_msgs and m not in recent and m not in always_keep
        ]
        if not to_summarize:
            return

        print(f"\n--- [CONTEXT] Summarization triggered ({self.total_tokens}/{self.token_limit} tokens) ---")
        print(f"--- [CONTEXT] Summarizing {len(to_summarize)} message(s):")
        for m in to_summarize:
            preview = m.content[:80] + "..." if len(m.content) > 80 else m.content
            print(f"--- [CONTEXT]   [{m.role}] ({m.token_count}t) {preview}")

        try:
            summary_text = self._summarize_fn(
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

        preview = summary_msg.content[:80] + "..." if len(summary_msg.content) > 80 else summary_msg.content
        print(f"--- [CONTEXT] -> Replaced with: [{summary_msg.role}] ({summary_msg.token_count}t) {preview}")
        print(f"--- [CONTEXT] Total tokens now: {self.total_tokens}/{self.token_limit}\n")
