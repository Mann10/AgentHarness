---
phase: 05-harness-runtime
plan: 07
subsystem: entry-point
tags: [runtime, refactor, main, entry-point, orchestrator]

# Dependency graph
requires:
  - phase: 05-05
    provides: RuntimeAPI orchestrator with Scheduler, EventBus, SessionManager
  - phase: 05-06
    provides: Refactored TUI as pure view layer consuming RuntimeAPI
provides:
  - main.py refactored to use RuntimeAPI as central orchestrator
  - All three CLI modes (REPL, TUI, worker) share unified lifecycle
  - Removed duplicate summarization code (now owned by RuntimeAPI)
affects:
  - harness/runtime.py — accessed via _session_manager and _create_agent for session commands

# Tech tracking
tech-stack:
  added: []
  patterns:
    - Entry point is thin: create config, create RuntimeAPI, start, dispatch to mode
    - REPL uses EventBus subscription for result delivery instead of direct agent.run()
    - Worker mode creates per-process RuntimeAPI with QueueManager for job persistence
    - TUI creates isolated RuntimeAPI, receives event-driven updates

key-files:
  created: []
  modified:
    - main.py — Refactored from 370 to 312 lines: RuntimeAPI wiring, no duplicate summarize, no top-level QueueManager

key-decisions:
  - "run_repl() uses RuntimeAPI.submit_prompt() with EventBus subscription for result delivery; plan's pattern works because subscribe completes before agent.run() internally awaits"
  - "run_worker() creates its own RuntimeAPI (per-process) and imports QueueManager locally for job persistence — no cross-tenant isolation needed (single-user tool)"
  - "run_tui() creates its own RuntimeAPI and passes to AgentHarnessTUI constructor; no QueueManager or agent lifecycle leaked"
  - "main() owns RuntimeAPI lifecycle for REPL; run_repl also shutdowns in its finally as safety net (shutdown is idempotent)"
  - "/new session command accesses runtime._session_manager and runtime._create_agent() since RuntimeAPI does not expose create_session() publicly — acceptable private-access pattern for REPL session management"

requirements-completed: [D-02, D-10, D-12, D-13]

# Metrics
duration: 3min
completed: 2026-07-26
---

# Phase 5 Plan 7: main.py RuntimeAPI Integration Summary

**Refactored main.py from inline wiring to RuntimeAPI central orchestrator — all three CLI modes (REPL, TUI, worker) share unified lifecycle through `from harness import RuntimeAPI`**

## Performance

- **Duration:** 3 min
- **Started:** 2026-07-26T21:25:53Z
- **Completed:** 2026-07-26T21:28:54Z
- **Tasks:** 1
- **Files modified:** 1

## Accomplishments

- `main()` creates `RuntimeAPI` instead of inline `queue_manager`/`store` wiring — satisfies D-02 (harness owns everything)
- `/new` and `/resume` session commands use `RuntimeAPI._session_manager` and `RuntimeAPI.switch_session()` — existing QueueManager (D-10) available only in worker path via local import
- `run_repl()` uses `RuntimeAPI.submit_prompt()` + EventBus `ResponseComplete` subscription instead of direct `agent.run()` — satisfies D-12 (pure Python in-process API) and D-13 (non-blocking submit)
- `run_tui()` creates `RuntimeAPI` and passes to `AgentHarnessTUI(runtime=runtime)` — no QueueManager or agent lifecycle in TUI
- `run_worker()` creates per-process `RuntimeAPI` with local `QueueManager` import and `is_busy` polling loop for job completion
- Removed `SUMMARIZATION_PROMPT` constant and `_make_summarize_fn()` — now owned by RuntimeAPI (no duplication)
- Removed top-level `from jobqueue.manager import QueueManager` and `from session import JSONLSessionStore`
- File reduced from 370 lines to 312 lines (58 lines removed net)
- All 34 existing tests continue to pass

## Task Commits

Each task was committed atomically:

1. **task 1: refactor main() to create RuntimeAPI and simplify dispatch** - `d134bae` (feat)

## Files Created/Modified

- `main.py` - Refactored from 370 to 312 lines: RuntimeAPI wiring, removed duplicate summarize code, QueueManager local import only in worker path, all 3 CLI modes use RuntimeAPI

## Decisions Made

- `run_repl()` uses EventBus subscription for result delivery. The subscribe-before-run pattern works because `RuntimeAPI.submit_prompt()` enqueues the task (non-blocking D-15) and the first `await` in the agent's run (LLM call) yields the event loop, allowing the subscription to complete before `ResponseComplete` fires.
- `run_worker()` creates per-process `RuntimeAPI` — no cross-tenant isolation concerns for a single-user tool (T-05-16 accepted per threat model).
- `/new` session command accesses `runtime._session_manager` and `runtime._create_agent()` (private API) since `RuntimeAPI` does not expose a public `create_session()` method. Acceptable for the REPL path which is a legacy UX mode.

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 2 - Missing Critical] `/new` session command must recreate agent for new session**
- **Found during:** task 1 (refactoring main.py)
- **Issue:** Plan's `/new` handler in `_handle_session_cmd` only creates a new session via `runtime._session_manager.create_session()`, but the Scheduler still holds the old Agent bound to the old session. Submitting a prompt after `/new` would use the wrong session.
- **Fix:** Added `await runtime._create_agent()` call after creating the new session, matching how `RuntimeAPI.switch_session()` works when loading an existing session. This shuts down the old agent and creates a new one bound to the new session.
- **Files modified:** main.py
- **Verification:** Agent is recreated with `runtime.active_session` as its session (same pattern as `RuntimeAPI._create_agent`). No test regression — all 34 tests pass.
- **Committed in:** d134bae (task 1 commit)

**2. [Rule 2 - Missing Critical] `/resume` and `/new` should save current session before switching**
- **Found during:** task 1 (refactoring main.py)
- **Issue:** Plan's `/resume` handler does not save the current session before switching. If the user has unsaved progress (e.g., new auto-title set after a response), that data would be lost.
- **Fix:** Added `await runtime._session_manager.save_session()` before switching to the new/target session, matching the original behavior.
- **Files modified:** main.py
- **Verification:** Session saved before switch; data preserved.
- **Committed in:** d134bae (task 1 commit)

---

**Total deviations:** 2 auto-fixed (both Rule 2 — missing critical functionality)
**Impact on plan:** Both fixes prevent data loss and ensure correct session routing. No scope creep.

## Issues Encountered

None — plan executed cleanly.

## Verification Results

```
$ python -c "import ast; ast.parse(open('main.py').read()); print('Syntax OK')"
PASS: Syntax OK

$ python main.py --help
PASS: argparser help displays correctly

$ grep 'from harness import RuntimeAPI' main.py
PASS: RuntimeAPI imported in main.py

$ grep -c 'SUMMARIZATION_PROMPT\|_make_summarize_fn' main.py
PASS: SUMMARIZATION_PROMPT and _make_summarize_fn removed

$ grep -c 'from jobqueue.manager import QueueManager' main.py
PASS: QueueManager only imported locally (0 at top level, 1 inside run_worker)

$ python -m pytest tests/ -x -q
PASS: 34 passed in 3.56s
```

## Self-Check: PASSED

- [x] `main.py` exists and is valid Python syntax
- [x] Commit `d134bae` exists for task 1
- [x] `from harness import RuntimeAPI` in imports
- [x] `SUMMARIZATION_PROMPT` and `_make_summarize_fn` removed
- [x] No top-level `QueueManager` or `JSONLSessionStore` import
- [x] `python main.py --help` works (returns argparser help, no crash)
- [x] All 34 tests pass

## Threat Flags

None — all new code stays within existing trust boundaries (in-process API calls, no new network endpoints).

## User Setup Required

None - no external service configuration required.

## Next Phase Readiness

- main.py is now thin: creates config, creates RuntimeAPI, starts it, dispatches to mode
- All three CLI paths (tui, worker, repl) share RuntimeAPI lifecycle
- Redundant code (summarize, store wiring) removed from entry point
- Phase 5 is complete — ready for next phase of development
