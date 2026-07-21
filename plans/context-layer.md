# Context Layer Module

## Goal
Introduce a `context` module that owns conversation state — structured messages, running token count, token limits, and automatic summarization — and integrate it into the LLM client and REPL loop.

## Files to Create

| File | Contents |
|---|---|
| `context/__init__.py` | Exports `Message`, `ConversationContext` |
| `context/message.py` | `Message` dataclass (role, content, token_count) |
| `context/context.py` | `ConversationContext` — owns messages, tracks total tokens, triggers summarization |

## Files to Modify

| File | Changes |
|---|---|
| `llm/base.py` | Change `chat()` signature to accept `ConversationContext`, add `chat_from_messages()` for internal use |
| `llm/openai_client.py` | Implement new signatures |
| `main.py` | Use `ConversationContext` instead of raw `list[dict]` |

## Design Details

### Message (`context/message.py`)

```python
@dataclass
class Message:
    role: str          # "system" | "user" | "assistant"
    content: str
    token_count: int = 0   # filled in by ConversationContext on add
```

- `role` is validated on construction — must be one of `system`, `user`, `assistant`

### ConversationContext (`context/context.py`)

**Constructor parameters:**
- `system_prompt: str | None` — optional system message prepended on init
- `count_tokens: Callable[[str], int]` — injected from the LLM client (single source of truth, no duplication)
- `token_limit: int` — from `Config.max_tokens`
- `summarize_fn: Callable[[list[dict]], str] | None` — optional callback for auto-summary
- `summarize_threshold: float = 0.75` — triggers auto-summary when `total_tokens > token_limit * threshold`
- `keep_recent_exchanges: int = 2` — number of recent user/assistant exchanges to preserve during summarization

**State:**
- `_messages: list[Message]` — ordered conversation history
- `total_tokens: int` — running sum of all `message.token_count`

**Key methods:**
- `add_message(msg: Message) -> None` — appends, counts tokens if needed, updates `total_tokens`, triggers `_maybe_summarize()`
- `add_user_message(content: str) -> None` — convenience wrapper
- `add_assistant_message(content: str) -> None` — convenience wrapper
- `to_llm_messages() -> list[dict]` — serializes to the `[{"role":..., "content":...}, ...]` format the OpenAI SDK expects

**Summarization flow (`_maybe_summarize`):**
1. Check if `total_tokens > token_limit * summarize_threshold`
2. Keep system prompt + last N exchanges untouched
3. Take everything in between → call `summarize_fn()` with those messages as `list[dict]`
4. Replace them with a single `Message(role="system", content="Previous summary: ...")`
5. Recompute `total_tokens`

### BaseLLMClient changes (`llm/base.py`)

```python
@abstractmethod
def chat(self, context: ConversationContext, **kwargs) -> str: ...

@abstractmethod
def chat_from_messages(self, messages: list[dict], **kwargs) -> str: ...
```

`chat()` is the public API — takes the full context object. `chat_from_messages()` is for internal use (e.g., the summarizer callback), taking raw message dicts to avoid circularity.

### OpenAIClient changes (`llm/openai_client.py`)

- `chat(context, **kwargs)` — calls `context.to_llm_messages()` internally, passes to the SDK
- `chat_from_messages(messages, **kwargs)` — same core logic, takes raw `list[dict]`
- Both share a private `_call_sdk(messages, **kwargs) -> str` helper to avoid duplication

### main.py changes

```python
context = ConversationContext(
    system_prompt=config.system_prompt,
    count_tokens=client.count_tokens,
    token_limit=config.max_tokens,
    summarize_fn=lambda msgs: client.chat_from_messages(
        [{"role": "system", "content": "Summarize the following concisely"}] + msgs,
        temperature=0.3,
    ),
)

while True:
    user_input = input("> ").strip()
    context.add_user_message(user_input)
    response = client.chat(context)
    context.add_assistant_message(response)
    print(response)
    print(f"[{context.total_tokens}/{config.max_tokens} tokens]")
```

## Open Questions / Edge Cases

| Concern | Proposal |
|---|---|
| **What if `summarize_fn` raises?** | Wrap in try/except inside `_maybe_summarize`, warn and skip |
| **What if all messages get summarized (no recent kept)?** | Always keep at least the latest user message |
| **Should `Message` validate `role`?** | Yes — raise `ValueError` if not one of `system\|user\|assistant` |
| **Should context be immutable-ish?** | Only `add_message` mutations; no public removal/mutation methods to keep tracking consistent |
| **Summarization during streaming?** | Not a concern yet — summarization would happen between turns, before the next user input |

## Implementation Order

1. Create `context/` package with `Message` and `ConversationContext`
2. Modify `BaseLLMClient` — new signature, add `chat_from_messages`
3. Modify `OpenAIClient` — implement both methods with shared helper
4. Update `main.py` — wire everything together
