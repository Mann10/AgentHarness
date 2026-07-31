---
phase: 10-token-streaming
plan: 02
subsystem: agent
tags: [streaming, events, asyncio, pytest, token-produced]

# Dependency graph
requires:
  - phase: 10-01
    provides: StreamChunk contract and stream_chat() implementation on BaseLLMClient/OpenAIClient
provides:
  - Agent `_stream_llm_call` helper iterating stream_chat() and emitting TokenProduced per text chunk
  - Both LLM call sites in Agent.run() (main loop + max-iterations forced path) routed through streaming
  - Migrated test_agent_events.py stubs (stream_chat-configured fakes) + new 4-test agent streaming suite
affects: [10-03 (TUI truncation marker + auto-scroll), 10-04 (end-to-end human verification)]

# Tech tracking
tech-stack:
  added: []
  patterns:
    - "All agent LLM calls stream via _stream_llm_call; TokenProduced emitted per content chunk (D-01/D-02)"
    - "Turn type decided by inspecting stream deltas, never pre-decided by agent (D-03)"
    - "Partial content never persisted: add_assistant_message called only after stream completes (D-05)"

key-files:
  created:
    - tests/test_agent_streaming.py
  modified:
    - agent/core.py
    - tests/test_agent_events.py

key-decisions:
  - "Followed plan verbatim: _stream_llm_call mirrors batch _call_sdk semantics — content=None for tool turns, raw content (possibly empty string) for text turns (no `content or None`)"
  - "TDD within the single atomic task: RED commit (migrated stubs + 4 failing tests) then GREEN commit (implementation)"
  - "REFACTOR phase skipped — final code matches the plan's spec exactly, no cleanup needed"

patterns-established:
  - "Streaming is the sole LLM call path for the agent; batch chat_from_messages remains only in RuntimeAPI._make_summarize_fn (out of scope)"

requirements-completed:
  - "D-01 (Agent streams every LLM call via the streaming path)"
  - "D-02 (TokenProduced events emitted only for text content)"
  - "D-03 (Client distinguishes turn type by inspecting stream deltas)"
  - "D-05 (Partial content not persisted to session JSONL)"
  - "D-08 (Streaming is TUI-only; REPL keeps batch behavior)"

# Metrics
duration: 2min
completed: 2026-07-31
---

# Phase 10 Plan 2: Agent TokenProduced Emission Summary

**Agent loop routed through `stream_chat()` via a new `_stream_llm_call` helper that emits `TokenProduced` per text chunk, with tool-call turns untouched and a fully green 43-test suite**

## Performance

- **Duration:** 2 min
- **Started:** 2026-07-31T15:47:50Z
- **Completed:** 2026-07-31T15:49:34Z
- **Tasks:** 1 (TDD: RED + GREEN commits)
- **Files modified:** 3

## Accomplishments

- Added `Agent._stream_llm_call` — iterates `self._llm.stream_chat(messages, tools=...)`, emits `TokenProduced(session_id, chunk)` for every non-empty content chunk, and returns `LLMResponse(content=None, tool_calls=...)` for tool turns vs `LLMResponse(content=joined, tool_calls=None)` for text turns (mirrors batch `_call_sdk` semantics exactly)
- Replaced both `chat_from_messages` call sites in `run()` (main loop + max-iterations forced path) — `grep chat_from_messages agent/core.py` now returns zero matches
- Migrated `tests/test_agent_events.py` `_make_stub_agent` to serve `stream_chat` via an async-generator fake that branches on `tools` truthiness; all existing event assertions unchanged and passing
- Created `tests/test_agent_streaming.py` with 4 tests: per-chunk TokenProduced with session_id and one concatenated persisted assistant message; zero token events on tool turns with intact ToolCallEvent/ToolResultEvent flow; mid-stream RuntimeError → single ErrorEvent with partial content absent from context (D-05) and no ResponseComplete; forced path streaming `Final text` with `ResponseComplete(forced=True)` and `AgentResult.forced is True`
- Verified D-08: `main.py` untouched (REPL still subscribes only to `"ResponseComplete"` at lines 178/190, no `TokenProduced` references); worker mode untouched
- Knowledge graph updated via `graphify update .` (598 nodes, 1303 edges, 26 communities)

## task Commits

Each task was committed atomically:

1. **task 1: Add _stream_llm_call to agent/core.py, migrate test_agent_events.py stubs, and write tests/test_agent_streaming.py (atomic)** — TDD split into two commits:
   - `2f10579` (test) — RED: migrate event stubs to stream_chat + add 4 failing streaming tests (5 failed as expected)
   - `f9ed130` (feat) — GREEN: `_stream_llm_call` + both call-site replacements (43 passed)

_Note: TDD tasks may have multiple commits (test → feat → refactor); REFACTOR was not needed._

## Files Created/Modified

- `agent/core.py` - Added `TokenProduced` to harness.events import block, `from tool.models import LLMResponse, ToolCall`, `_stream_llm_call` helper (between `switch_session` and `run`), both call sites switched to the streaming path
- `tests/test_agent_events.py` - `_make_stub_agent` LLM mock now configures `llm.stream_chat = _fake_stream` (async generator branching on `no_tools`/`tools`); imports extended with `StreamChunk`
- `tests/test_agent_streaming.py` - New: `StreamingStubLLM` stub (yields tool_calls only when `tools` truthy), `_make_agent` helper (registry with `AsyncMock` call_tool), 4 async tests

## Decisions Made

- Followed plan verbatim — no deviations. The acknowledged edge-case drift vs the batch path (empty-stream → persisted `content=""`; mixed content+tool_calls → content dropped) is deliberate per D-01/D-02 and not flagged.
- TDD commit structure used within the single merged task (test commit before feat commit), satisfying the plan's "do NOT split the task" constraint at task granularity while keeping RED/GREEN gates visible in history.

## Deviations from Plan

None - plan executed exactly as written.

## TDD Gate Compliance

- RED gate: `2f10579` (`test(10-02): add failing streaming tests and migrate event stubs to stream_chat`) — ran with 5 failures (4 new streaming tests + migrated tool-events test) against the unmodified batch-path agent
- GREEN gate: `f9ed130` (`feat(10-02): route agent LLM calls through streaming path emitting TokenProduced`) — full suite 43 passed
- REFACTOR gate: skipped intentionally — final implementation is the plan's exact spec; no cleanup warranted

## Issues Encountered

None.

## User Setup Required

None - no external service configuration required.

## Next Phase Readiness

- Agent now publishes `TokenProduced` for every text chunk → EventBus → RPC `token` notification → TUI (existing pipeline from Phase 9 is now live end-to-end)
- Ready for 10-03 (TUI truncation marker for D-04 + auto-scroll for D-06, D-07 verification) — the TUI `appendToken`/`StreamingText` path now has a real producer to consume
- 10-04 (end-to-end human verification) can validate the full streaming UX

---

## Self-Check: PASSED

- Files on disk: `agent/core.py`, `tests/test_agent_events.py`, `tests/test_agent_streaming.py`, `10-02-SUMMARY.md` — all FOUND
- Commits in git log: `2f10579` (test/RED), `f9ed130` (feat/GREEN) — both FOUND
- Full suite: `python -m pytest tests/ -q` → 43 passed
- Acceptance criteria: all greps verified (no `chat_from_messages` in agent/core.py; 3 `TokenProduced` matches; no `finally`/`except asyncio.CancelledError`; 4 test functions present; `main.py` untouched)

---

*Phase: 10-token-streaming*
*Completed: 2026-07-31*
