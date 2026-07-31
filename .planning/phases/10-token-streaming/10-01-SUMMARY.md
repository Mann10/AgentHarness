---
phase: 10-token-streaming
plan: 01
subsystem: api
tags: [llm, streaming, openai-sdk, async-generator, python]

# Dependency graph
requires:
  - phase: 09-ts-tui-json-rpc
    provides: TokenProduced event + RPC token notification + TUI StreamingText rendering (dead code awaiting a producer)
provides:
  - "StreamChunk dataclass contract (content / tool_calls) in llm/base.py"
  - "stream_chat async generator over AsyncOpenAI stream=True with per-delta text yields"
  - "Tool-call turn assembly from fragmented deltas into a single final ToolCall chunk"
  - "Typed error mapping (LLMConnectionError/LLMResponseError) for create() and mid-stream failures"
  - "_convert_tools helper extracted from _call_sdk, shared by batch and streaming paths"
  - "5-test streaming suite (tests/test_stream_chat.py) covering text, tool-call, error, and kwargs paths"
affects: [10-token-streaming (10-02 agent TokenProduced emission, 10-03 TUI truncation), agent/core.py consumers]

# Tech tracking
tech-stack:
  added: [openai SDK streaming (already a dependency, now exercised), httpx (test-only, transitive dep)]
  patterns: ["async generator as LLM streaming interface", "delta-based turn-type detection (content vs tool_calls)", "module-level _convert_tools shared by batch/streaming paths"]

key-files:
  created: [tests/test_stream_chat.py]
  modified: [llm/base.py, llm/openai_client.py]

key-decisions:
  - "stream_chat takes messages: list[dict] (not ConversationContext) so the agent can pass Session.to_llm_messages() with the system prompt — base signature fixed from sync Generator to AsyncIterator[StreamChunk]"
  - "Turn type decided in the client by inspecting stream deltas (D-03): text deltas yield per-delta content chunks; tool_calls deltas yield zero content chunks then one final assembled ToolCall chunk"
  - "Plain def (not async def) abstract method returning AsyncIterator[StreamChunk] — implementations are async generator functions; calling them returns the AsyncIterator"
  - "json.loads on tool-call arguments intentionally unwrapped (mirrors _call_sdk line 84); malformed args propagate as exceptions the agent surfaces as ErrorEvent"
  - "Test mid-stream errors use APIStatusError (subclass of APIError, has status_code) — bare APIError in openai 2.48.0 lacks status_code"

patterns-established:
  - "Streaming contract: AsyncIterator[StreamChunk], one chunk per SDK delta, no client-side batching"
  - "Error mapping parity: stream_chat catches the same exceptions at the same points as _call_sdk (create call + iteration)"

# Metrics
duration: 3min
completed: 2026-07-31
---

# Phase 10 Plan 1: LLM Client Streaming (StreamChunk + stream_chat) Summary

**StreamChunk dataclass contract in llm/base.py plus a stream_chat async generator over AsyncOpenAI stream=True — per-delta text yields for text turns, single assembled ToolCall chunk for tool-call turns, with typed error mapping matching _call_sdk**

## Performance

- **Duration:** 3 min
- **Started:** 2026-07-31T15:41:46Z
- **Completed:** 2026-07-31T15:44:58Z
- **Tasks:** 2
- **Files modified:** 3

## Accomplishments
- Defined the `StreamChunk` contract (`content: str = ""`, `tool_calls: list[ToolCall] | None = None`) in `llm/base.py`, replacing the broken `async def stream_chat(context) -> Generator[str, None, None]` abstract signature with `def stream_chat(messages, *, tools=...) -> AsyncIterator[StreamChunk]` — so the agent can pass `Session.to_llm_messages()` with the system prompt (D-01/D-03)
- Implemented `stream_chat` in `llm/openai_client.py` as an async generator over `chat.completions.create(stream=True)`: yields one `StreamChunk(content=...)` per content delta; for tool-call turns yields zero content chunks then a single final chunk with the assembled `ToolCall` list (id/name/arguments reassembled from fragmented deltas, ordered by `tc.index`)
- Error mapping covers both failure points: `APIConnectionError` → `LLMConnectionError` and `APIError` → `LLMResponseError`, on the `create()` call AND mid-iteration, matching `_call_sdk` semantics
- Extracted the inline tools-conversion from `_call_sdk` into a module-level `_convert_tools` helper now shared by both `_call_sdk` and `stream_chat` (no behavior change to the batch path)
- 5 new streaming tests pass; full pytest suite green at 39 tests (34 existing + 5 new)

## task Commits

Each task was committed atomically:

1. **task 1: Define StreamChunk contract in llm/base.py + implement stream_chat in llm/openai_client.py** - `5de9041` (feat)
2. **task 2: Write tests/test_stream_chat.py covering text, tool-call, and error paths** - `ec6452f` (test)

**Plan metadata:** see orchestrator commit (executor does not commit .planning/STATE.md or ROADMAP.md)

_Note: Plan is `type: execute` (not `type: tdd`) — the TDD-style RED/GREEN gate sequence does not apply. Both tasks carry `tdd="true"` flags but the plan explicitly orders implementation (task 1) before tests (task 2); tests were written to the plan's exact spec and passed immediately (no RED commit). Test coverage is post-hoc verification, not test-first._

## Files Created/Modified
- `llm/base.py` - Added `StreamChunk` dataclass (content/tool_calls); replaced broken abstract `stream_chat` signature with `def stream_chat(messages, *, tools=...) -> AsyncIterator[StreamChunk]`; imports updated (`AsyncIterator`, `dataclass`, `ToolCall`), `Generator` import removed
- `llm/openai_client.py` - Added `_convert_tools` helper; `_call_sdk` now uses it; replaced `stream_chat` NotImplementedError stub with full async generator implementation; `Generator` import removed
- `tests/test_stream_chat.py` - 5 tests: text delta streaming, tool-call assembly from fragments, connection error mapping, mid-stream error mapping, tools→API kwargs conversion

## Decisions Made
- `stream_chat` accepts `messages: list[dict]` rather than `ConversationContext` so callers preserve system-prompt behavior via `Session.to_llm_messages()` — this is why the base signature changed (per plan CRITICAL CONTEXT)
- Turn type is decided inside the client by inspecting stream deltas (D-03) — the caller never pre-decides; tool-call turns emit a single final chunk rather than per-fragment chunks
- Mid-stream error tests use `APIStatusError` (the SDK class that actually carries `status_code`) instead of bare `APIError`, which lacks `status_code` in openai 2.48.0

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 1 - Bug] Mid-stream error test used bare APIError which lacks status_code in openai 2.48.0**
- **Found during:** task 2 (test_stream_chat_maps_stream_error)
- **Issue:** The plan specified constructing `APIError("boom", request=None, body=None)` for the mid-stream error test. In openai 2.48.0 the base `APIError.__init__` sets `message`/`request`/`body` but NOT `status_code` (only subclasses such as `APIStatusError` set it). The implementation's `f"API error during stream: {e.status_code} {e.message}"` (plan-exact code) therefore crashed with `AttributeError: 'APIError' object has no attribute 'status_code'` instead of surfacing `LLMResponseError`.
- **Fix:** Changed the test to raise `APIStatusError("boom", response=httpx.Response(500, request=...), body=None)` — the class the SDK actually raises for 4xx/5xx mid-stream. `APIStatusError` is a subclass of `APIError` so the implementation's `except APIError` clause still catches it, and `status_code`/`message` resolve correctly. Implementation untouched — it is correct for real SDK-raised errors.
- **Files modified:** tests/test_stream_chat.py
- **Verification:** `python -m pytest tests/test_stream_chat.py -v` → 5 passed; full suite 39 passed
- **Committed in:** ec6452f (task 2 commit)

---

**Total deviations:** 1 auto-fixed (1 bug in plan's test spec)
**Impact on plan:** Auto-fix necessary for the error-path test to exercise the intended mapping. No scope creep; no implementation changes beyond the plan.

## Issues Encountered
- Plan's `APIError("boom", request=None, body=None)` test form did not match openai 2.48.0's base exception (missing `status_code` attribute) — resolved via `APIStatusError` with a real httpx response (see deviation 1)

## TDD Gate Compliance

Plan-level RED/GREEN/REFACTOR gate sequence does not apply: this plan is `type: execute`, not `type: tdd`. Both tasks are flagged `tdd="true"` but the plan orders implementation before tests, so there is no RED (failing test) commit and no GREEN-after-RED sequence. Verified in git log: `5de9041` (feat, task 1) precedes `ec6452f` (test, task 2).

## User Setup Required

None - no external service configuration required.

## Next Phase Readiness
- **10-02 (Agent TokenProduced emission):** consumes `stream_chat` directly — agent will iterate the async generator, emit `TokenProduced` per text chunk, and accumulate content; tool-call turns are identified by the final chunk's `tool_calls` field. The `messages`-based signature (not `context`) means 10-02 must pass `Session.to_llm_messages()` for system-prompt parity
- **10-03 (TUI truncation):** consumes the same chunks via the RPC `token` notification path already built in Phase 9
- No blockers. The dead-code gap identified in 09-VERIFICATION Gap 1 ("stream_chat() raises NotImplementedError") is closed.

---
*Phase: 10-token-streaming*
*Completed: 2026-07-31*

## Self-Check: PASSED

- [x] `llm/base.py` exists — StreamChunk dataclass + AsyncIterator[StreamChunk] abstract signature
- [x] `llm/openai_client.py` exists — stream_chat async generator, _convert_tools, stream=True
- [x] `tests/test_stream_chat.py` exists — all 5 test functions present, 5 passed
- [x] `10-01-SUMMARY.md` exists
- [x] Commit `5de9041` (feat 10-01) present in git log
- [x] Commit `ec6452f` (test 10-01) present in git log
- [x] Full pytest suite: 39 passed (34 existing + 5 new), 0 failures
- [x] graphify update completed (582 nodes, 1232 edges)
