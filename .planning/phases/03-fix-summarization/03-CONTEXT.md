# Phase 3: Fix Summarization - Context

**Gathered:** 2026-07-25
**Status:** Ready for planning

<domain>
## Phase Boundary

Fix the broken conversation summarization system. Resolve critical `NameError` crash, O(n²) performance bug, and latent `LLMResponse`→`str` type mismatch. Improve the summarization prompt and error handling. No new features outside the summarization subsystem.

</domain>

<decisions>
## Implementation Decisions

### Summarization Strategy
- **D-01:** Once token threshold is breached (total_tokens > token_limit * summarize_threshold), summarize ALL messages except recent exchanges
- **D-02:** `_keep_recent_exchanges` defaults to **1** — the last assistant+user pair survives alongside the summary
- **D-03:** Insert summary at index 0 (conversation messages), system messages are owned by `Session`, not `ConversationContext`
- **D-04:** On subsequent threshold breaches, the summary + recent exchanges get compressed further together
- **D-05:** Remove summarized messages in O(n) using a set-based list comprehension

### Bug Fixes
- **D-06:** Replace `system_msgs` undefined reference with `0` at `context/context.py:125`
- **D-07:** Fix `_make_summarize_fn` in `main.py:18-28` — extract `.content` from `LLMResponse` to return proper `str`
- **D-08:** Remove O(n²) `.remove()` loop — use `to_summarize_set` + list comprehension

### Error Handling
- **D-09:** **Soft degrade** — if `summarize_fn` raises, log a warning, skip summarization, continue running
- **D-10:** Do not crash the agent or propagate errors to the user visibly — print notice to terminal

### Summarization Prompt
- **D-11:** Prompt is a structured report format, not a narrative
- **D-12:** Sections: Current goal, Key decisions, Progress made, Files/tools touched, Open questions, Technical context
- **D-13:** Result is bullet-point structured output, not prose
- **D-14:** Prompt style inspired by Claude Code's internal summarization

### OpenCode's Discretion
- Exact wording of the summarization prompt within the agreed structure
- Error message format
- Configurable threshold variable name
</decisions>

<canonical_refs>
## Canonical References

No external specs — requirements are fully captured in decisions above.

The codebase map at `.planning/codebase/` provides full context of existing code:
- `context/context.py` — Target file for summarization fixes
- `main.py` — Where `_make_summarize_fn` is defined and broken
- `context/message.py` — Message dataclass used by summarization
- `session/models.py` — Session owns system prompt, context handles conversation messages only
- `.planning/codebase/CONCERNS.md` — Documents the known bugs and their impact
</canonical_refs>

<code_context>
## Existing Code Insights

### Reusable Assets
- `context/context.py:75-136` — `_maybe_summarize()` method, needs rework
- `main.py:18-28` — `_make_summarize_fn` factory, needs `.content` extraction
- `context/message.py` — `Message` dataclass with `role`, `content`, `token_count`

### Established Patterns
- `async`/`await` throughout — all I/O uses asyncio
- `Callable[[list[dict]], Awaitable[str]]` type for `summarize_fn`
- Constructor dependency injection (count_tokens, token_limit injected)

### Integration Points
- `ConversationContext._maybe_summarize()` called from `add_message()` and `add_assistant_tool_message()`
- `Session.create()` and `Session.restore_context()` pass `summarize_fn` through to `ConversationContext`
- `main.py:_make_summarize_fn()` creates the actual summarization lambda
</code_context>

<specifics>
## Specific Ideas

- "make summarization proper" — full rework, not just the crash
- Summarization prompt should match the style Claude Code uses internally
- "once the threshold is breached it will summarize all the message and keep the summary only in the context"

</specifics>

<deferred>
## Deferred Ideas

- Testing infrastructure — separate phase
- Tool system hardening (remove_provider, health-check) — separate phase
- Session store global directory — backlog

None — discussion stayed within phase scope
</deferred>

---

*Phase: 03-fix-summarization*
*Context gathered: 2026-07-25*
