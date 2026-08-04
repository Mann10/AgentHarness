---
phase: 05-harness-runtime
plan: 05
subsystem: runtime
tags: [runtime-api, orchestrator, lifecycle, scheduler, event-bus, session-manager]

# Dependency graph
requires:
  - phase: 05-01
    provides: EventBus and typed event dataclasses
  - phase: 05-02
    provides: SessionManager wrapping JSONLSessionStore
  - phase: 05-04
    provides: Scheduler with one-turn dispatch and backlog
provides:
  - RuntimeAPI — top-level orchestrator owning EventBus, Scheduler, SessionManager, Agent
  - harness/__init__.py barrel exports with lazy import for circular-safe access
  - Config.max_tool_iterations — configuration field for agent iteration limit
affects:
  - 05-07: main.py integration (removes inline _make_summarize_fn from main.py)
  - 06-textual-tui: TUI consumes RuntimeAPI for prompt submission and event subscription

# Tech tracking
tech-stack:
  added: []
  patterns:
    - Orchestrator pattern: RuntimeAPI owns and wires all subsystems
    - Lazy module-level imports via __getattr__ for circular dependency resolution
    - Property-based EventBus exposure for TUI subscription (D-14)

key-files:
  created:
    - harness/runtime.py — RuntimeAPI orchestrator class (167 lines)
    - tests/test_runtime.py — 7-test async test suite
  modified:
    - harness/__init__.py — barrel exports with lazy RuntimeAPI/Scheduler import
    - harness/scheduler.py — guard cancel() against None _current_task
    - config.py — added max_tool_iterations field

key-decisions:
  - "submit_prompt() auto-creates session if none active — TUI doesn't need manual session init"
  - "_create_agent() shuts down old agent before creating new one — clean session switch"
  - "backlog_maxsize=10 — bounded backlog prevents OOM (security mitigation per RESEARCH.md)"
  - "event_bus property exposes EventBus for TUI subscription without exposing scheduler internals"
  - "Scheduler wires Agent._emit to bus.publish in its __init__ — Runtime doesn't need to do this explicitly"
  - "_make_summarize_fn duplicated from main.py — will be removed from main.py in Plan 05-07"
  - "Circular import (agent→harness.events→harness→agent) resolved via lazy __getattr__ in __init__.py"

patterns-established:
  - "Lazy module-level import via __getattr__ for symbols with circular dependencies"
  - "Orchestrator owns subsystems, exposes narrow public API (4 methods), delegates to subsystem classes"

requirements-completed: [D-02, D-12, D-13]

# Metrics
duration: 4 min
completed: 2026-07-26
---

# Phase 5 Plan 5: RuntimeAPI Summary

**RuntimeAPI orchestrator class owning EventBus, Scheduler, SessionManager, and Agent with lazy-import barrel exports and full test coverage**

## Performance

- **Duration:** 4 min
- **Started:** 2026-07-26T21:14:07Z
- **Completed:** 2026-07-26T21:18:20Z
- **Tasks:** 3 (4 commits)
- **Files modified:** 5 (2 created, 3 modified)

## Accomplishments

- RuntimeAPI class with 4 public API methods (D-13): submit_prompt, cancel, list_sessions, switch_session
- Lifecycle management: start() creates session+agent+scheduler, shutdown() saves+shuts down gracefully
- event_bus property exposes EventBus for TUI subscription (D-14)
- submit_prompt() is non-blocking (D-15) — delegates to Scheduler, returns immediately
- Auto-creates session if none active — TUI works without manual session init
- _create_agent() handles agent re-creation for session switches
- Config.max_tool_iterations added (required by RuntimeAPI but missing from Config)
- harness/__init__.py barrel exports all public types with lazy imports to break circular dependency
- Scheduler.cancel() guarded against None current_task (pre-existing bug)
- 7-test async test suite covering API surface, lifecycle, submit/cancel, event_bus property

## Task Commits

Each task was committed atomically:

1. **task 1: create harness/runtime.py with RuntimeAPI class** - `ebd6c53` (feat)
2. **task 2: create harness/__init__.py with barrel exports** - `8a3ee4a` (feat)
3. **task 3: create tests/test_runtime.py** - `83bddb4` (test)
4. **fix: circular import + scheduler cancel guard** - `2415c67` (fix)

## Files Created/Modified

- `harness/runtime.py` - RuntimeAPI orchestrator (167 lines)
- `harness/__init__.py` - Barrel exports with lazy import for circular safety (38 lines)
- `harness/scheduler.py` - Guard cancel() against None _current_task
- `config.py` - Added max_tool_iterations field
- `tests/test_runtime.py` - 7-test async test suite

## Decisions Made

- `submit_prompt()` auto-creates session if none active — TUI works without manual session init
- `_create_agent()` shuts down old agent before creating new one — handles session switch cleanly
- `backlog_maxsize=10` — bounded backlog prevents OOM (security mitigation per RESEARCH.md)
- `event_bus` property exposes EventBus for TUI subscription (D-14) without exposing scheduler
- Scheduler wires Agent._emit to bus.publish in its `__init__` — Runtime doesn't need to do this explicitly
- `_make_summarize_fn` is duplicated from main.py — will be removed from main.py in Plan 05-07
- No direct dependence on jobqueue/ — worker path is separate (D-04, D-10)
- Circular import resolved via lazy `__getattr__` in `harness/__init__.py` (agent imports harness.events which triggers harness package init)

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 2 - Missing Critical] Added `max_tool_iterations` field to Config**
- **Found during:** task 1 (creating runtime.py)
- **Issue:** RuntimeAPI code uses `self._config.max_tool_iterations` when constructing Agent, but Config dataclass had no such field. Would cause `AttributeError` at runtime.
- **Fix:** Added `max_tool_iterations: int = 15` (env var: `MAX_TOOL_ITERATIONS`) to Config dataclass in config.py
- **Files modified:** config.py
- **Verification:** `python -c "from config import Config; c=Config(); print(c.max_tool_iterations)"` returns 15
- **Committed in:** ebd6c53 (task 1 commit)

**2. [Rule 3 - Blocking] Resolved circular import (agent ↔ harness) in harness/__init__.py**
- **Found during:** task 3 (running test collection)
- **Issue:** agent/core.py imports from harness.events, which triggers harness/__init__.py. That eagerly imported RuntimeAPI (which imports Agent) and Scheduler (which imports Agent), causing ImportError: "cannot import name Agent from partially initialized module agent"
- **Fix:** Replaced eager imports with lazy `__getattr__` for RuntimeAPI and Scheduler symbols in harness/__init__.py
- **Files modified:** harness/__init__.py
- **Verification:** `from harness import RuntimeAPI, Scheduler, EventBus` succeeds in any import order
- **Committed in:** 2415c67

**3. [Rule 1 - Bug] Guarded scheduler.cancel() against None _current_task**
- **Found during:** task 3 (running test_runtime_shutdown_after_start)
- **Issue:** RuntimeAPI.shutdown() calls scheduler.shutdown() -> cancel(), which calls `await asyncio.wait_for(self._current_task, timeout=3.0)` without checking if `_current_task` is None. When no prompts were submitted, `_current_task` is None, causing `TypeError: object NoneType can't be used in 'await' expression`.
- **Fix:** Added `if self._current_task is not None:` guard around the wait_for and follow-up cancel in scheduler.cancel()
- **Files modified:** harness/scheduler.py
- **Verification:** `test_runtime_start_creates_session_and_agent` passes — shutdown without prompts no longer crashes
- **Committed in:** 2415c67

---

**Total deviations:** 3 auto-fixed (1 missing critical, 1 blocking, 1 bug)
**Impact on plan:** All auto-fixes essential for correctness (circular import crash, None dereference crash, missing Config field). No scope creep.

## Issues Encountered

- Circular import between `agent` and `harness` packages: agent/core.py imports harness.events, harness/__init__.py imports runtime.py (which imports agent) → resolved via lazy `__getattr__` pattern
- Existing scheduler.cancel() bug surfaced by RuntimeAPI test: None `_current_task` caused crash on shutdown without prompts → fixed with None guard

## Self-Check: PASSED

```
$ python -c "from harness.runtime import RuntimeAPI; print('RuntimeAPI importable')"
RuntimeAPI importable

$ python -c "from harness import RuntimeAPI, EventBus, Scheduler, SessionManager, CancellationToken, TurnStarted, ResponseComplete; print('All harness exports importable')"
All harness exports importable

$ python -m pytest tests/test_runtime.py -x -q
.......                                                                  [100%]
7 passed in 1.47s

$ python -m pytest tests/ -x -q
..................................                                       [100%]
34 passed in 3.49s
```

## Threat Flags

None — all new code stays within existing trust boundaries (in-process D-12, no new network endpoints or auth paths).

## User Setup Required

None - no external service configuration required.

## Next Phase Readiness

- RuntimeAPI ready for integration into main.py (Plan 05-07) and TUI (Phase 6)
- All 4 API methods (D-13) exposed and tested
- EventBus accessible via property for TUI subscription (D-14)
- Calendar: submit_prompt() returns immediately (D-15)

---

*Phase: 05-harness-runtime*
*Completed: 2026-07-26*
