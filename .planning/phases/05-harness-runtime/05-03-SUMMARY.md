---
phase: 05-harness-runtime
plan: 03
subsystem: agent
tags: events, emit-callback, agent-lifecycle, pytest

# Dependency graph
requires:
  - phase: 05-harness-runtime (plan 01)
    provides: Typed event dataclasses (TurnStarted, ToolCallEvent, ToolResultEvent, ResponseComplete, ErrorEvent)
  - phase: 05-harness-runtime (plan 00)
    provides: test infrastructure (pytest.ini, conftest.py)
provides:
  - Agent with event emission hooks for Runtime EventBus observation
  - Agent event emission test suite (5 tests)
affects:
  - 05-harness-runtime (plan 04: Scheduler consumes Agent's events)

# Tech tracking
tech-stack:
  added: []
  patterns:
    - Callback injection with no-op default for backward compatibility
    - Lifecycle point emission at natural agent run() boundaries

key-files:
  created:
    - tests/test_agent_events.py — 5-test suite covering agent event emission
  modified:
    - agent/core.py — Added emit callback, 5 lifecycle emit points, error handler
    - harness/events.py — Added `forced` field to ResponseComplete

key-decisions:
  - "5 lifecycle emission points: TurnStarted, ToolCallEvent (per tool), ToolResultEvent (per result), ResponseComplete (text + forced), ErrorEvent"
  - "ErrorEvent wraps entire run() body in try/except Exception (not CancelledError — BaseException)"
  - "ToolCallEvent arguments field accepts dict | None from ToolCall.arguments"
  - "ResponseComplete.forced distinguishes natural text response from max-iterations forced response"

patterns-established:
  - "Emit callback: Callable[[Any], Awaitable[None]] | None with lambda _: noop fallback"
  - "Lifecycle emission: insert await self._emit(EventType(...)) at natural run() boundaries"
  - "Error wrapping: try/except Exception around main body, emit ErrorEvent, re-raise"

requirements-completed: [D-03, D-07]

# Metrics
duration: 15 min
completed: 2026-07-26
---

# Phase 5 Plan 03: Agent Event Emission Hooks Summary

**Agent.__init__ accepts optional emit callback (no-op default), run() emits TurnStarted, ToolCallEvent, ToolResultEvent, ResponseComplete, and ErrorEvent at natural lifecycle points — with 5-test suite verifying the mechanism**

## Performance

- **Duration:** 15 min
- **Started:** 2026-07-26T19:30:00Z
- **Completed:** 2026-07-26T19:45:00Z
- **Tasks:** 2
- **Files modified:** 3

## Accomplishments

- **Agent emission hooks** — `Agent.__init__` accepts `emit: Callable | None = None` with no-op fallback. `Agent.run()` emits 5 event types at natural lifecycle points: `TurnStarted` after user message, `ToolCallEvent` per tool call, `ToolResultEvent` per result, `ResponseComplete` on text or forced return, `ErrorEvent` on exception (re-raised).
- **Backward compatibility** — Existing callers (REPL, worker mode) pass no `emit` kwarg, get the no-op default. Zero breakage.
- **Event type fix** — Added `forced: bool = False` field to `ResponseComplete` dataclass to support the forced-text-response emission point (distinguishes natural vs max-iterations responses).
- **Test suite** — 5 tests covering emit callback acceptance, backward compat without emit, TurnStarted emission, ResponseComplete emission, and tool event (ToolCallEvent + ToolResultEvent) emission.

## Task Commits

Each task was committed atomically:

1. **Task 1: Add emit callback to Agent.__init__ and run()** - `cf6d58f` (feat)
2. **Task 2: Create tests/test_agent_events.py** - `66bf6fd` (test)

**Plan metadata:** _pending (final metadata commit after SUMMARY.md)_

## Files Created/Modified

- `agent/core.py` — Modified: added event emission hooks at 5 lifecycle points (184 lines, 143-line Agent class)
- `harness/events.py` — Modified: added `forced: bool = False` to ResponseComplete dataclass
- `tests/test_agent_events.py` — Created: 5-test suite for agent event emission (120 lines)

## Decisions Made

- **5 emission points** matched to Agent.run() lifecycle: TurnStarted (prompt received), ToolCallEvent (before tool execution), ToolResultEvent (after tool result), ResponseComplete (text response at early return and forced return), ErrorEvent (exception caught and re-raised).
- **ToolCallEvent.arguments** accepts `dict | None` from ToolCall.arguments — allows null arguments case.
- **ResponseComplete.forced** field distinguishes natural early return vs. max-iterations forced return — useful for subscribers to know response quality.
- **except Exception** (not bare except) correctly avoids catching `CancelledError` which inherits from `BaseException`.

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 1 - Bug] Test used MagicMock for tool_calls, fails with dataclasses.asdict**
- **Found during:** Task 2 (test creation)
- **Issue:** The plan's test code used `MagicMock` for `LLMResponse.tool_calls`, but `agent/core.py` passes these through `self._context.add_assistant_tool_message()` which calls `dataclasses.asdict()` on each tool call — MagicMock instances don't work with `asdict()`.
- **Fix:** Replaced `MagicMock` tool calls with real `ToolCall(id="call_1", name="get_weather", arguments={"location": "NYC"})` objects from `tool.models`.
- **Files modified:** `tests/test_agent_events.py`
- **Verification:** All 5 tests pass with the fix.
- **Committed in:** `66bf6fd` (task 2 commit)

**2. [Rule 1 - Bug] Missing `forced` field in ResponseComplete event dataclass**
- **Found during:** Task 2 (test execution — `test_agent_works_without_emit` failed)
- **Issue:** `Agent.run()` passes `forced=True` when creating `ResponseComplete` at the forced-text-response point, but `harness/events.py` `ResponseComplete` dataclass didn't have a `forced` field.
- **Fix:** Added `forced: bool = False` to `ResponseComplete` dataclass in `harness/events.py`.
- **Files modified:** `harness/events.py`
- **Verification:** All 20 tests pass (15 existing + 5 new).
- **Committed in:** `66bf6fd` (task 2 commit)

---

**Total deviations:** 2 auto-fixed (2 Rule 1 bugs)
**Impact on plan:** Minor fixes needed for correctness. No scope creep.

## Issues Encountered

- **Pre-existing changes in agent/core.py:** The agent/core.py file already contained all the emit hook changes (uncommitted) before this plan started. Most likely from a prior step. Verified the changes matched the plan exactly, then committed them.
- **Other pre-existing modifications:** `main.py`, `requirements.txt`, `graphify-out/`, `jobqueue/`, `tui/` all had uncommitted changes from prior work — left untouched per scope boundary rule.

## Verification Results

- ✅ `python -c "from agent.core import Agent; help(Agent.__init__)"` — shows `emit` parameter with correct type signature
- ✅ `python -m pytest tests/test_agent_events.py -x -q` — 5 passed
- ✅ `python -m pytest tests/ -x -q` — 20 passed (15 existing + 5 new, no breakage)
- ✅ Must_have truths: All 7 truths verified
- ✅ Must_have artifacts: agent/core.py (184 lines, ≥135), tests/test_agent_events.py (120 lines, ≥60)
- ✅ Must_have key_links: agent/core.py imports from harness/events, calls await self._emit()

## User Setup Required

None - no external service configuration required.

## Next Phase Readiness

- Agent event emission hooks complete — Scheduler can now observe agent execution via EventBus
- Next plan (05-04 Scheduler) can consume these events through the EventBus

## Self-Check: PASSED

All claims verified:
- [x] `agent/core.py` exists (184 lines, has `class Agent` with `self._emit`)
- [x] `tests/test_agent_events.py` exists (120 lines, 5 tests)
- [x] `harness/events.py` has `forced` field on ResponseComplete
- [x] Commit cf6d58f exists: `feat(05-harness-runtime-03): add event emission hooks to Agent.__init__ and run()`
- [x] Commit 66bf6fd exists: `test(05-harness-runtime-03): add agent event emission test suite`
- [x] `python -m pytest tests/test_agent_events.py -x -q` — 5 passed
- [x] `python -m pytest tests/ -x -q` — 20 passed

---

*Phase: 05-harness-runtime*
*Completed: 2026-07-26*
