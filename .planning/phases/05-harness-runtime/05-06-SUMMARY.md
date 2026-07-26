---
phase: 05-harness-runtime
plan: 06
subsystem: tui
tags: [tui, event-bus, runtime-api, refactor, view-layer]

# Dependency graph
requires:
  - phase: 05-01
    provides: EventBus and typed event dataclasses
  - phase: 05-05
    provides: RuntimeAPI orchestrator with event_bus property
provides:
  - Refactored TUI as pure view layer consuming RuntimeAPI and EventBus
  - StatusBar with processing indicator and last-result display
affects:
  - main.py — TUI constructor now takes RuntimeAPI instead of QueueManager
  - 05-07: worker/repl mode retains legacy update_status() until refactored

# Tech tracking
tech-stack:
  added: []
  patterns:
    - Reactive TUI: event subscription in on_mount, handlers update widgets
    - Pure view layer: TUI owns no agent lifecycle or queue management

key-files:
  created: []
  modified:
    - tui/app.py — Refactored from 101 to 130 lines: RuntimeAPI dependency, 6 event handlers, no QueueManager
    - tui/widgets/status_bar.py — Added update_processing() and update_last_result() methods

key-decisions:
  - "on_row_selected adapted to work without QueueManager (no job lookup available in event-driven mode)"
  - "EventBus imported from harness.event_bus (separate import from RuntimeAPI) for clean dependency separation"
  - "StatusBar retains legacy update_status() for worker/repl backward compat until Plan 05-07"

requirements-completed: [D-01, D-04, D-14]

# Metrics
duration: 2min
completed: 2026-07-26
---

# Phase 5 Plan 6: TUI as Pure View Layer Summary

**Refactored TUI from queue-manager worker pattern to reactive RuntimeAPI consumer with EventBus event subscription and processing indicator**

## Performance

- **Duration:** 2 min
- **Started:** 2026-07-26T21:20:35Z
- **Completed:** 2026-07-26T21:22:38Z
- **Tasks:** 2
- **Files modified:** 2

## Accomplishments

- TUI no longer imports QueueManager or manages agent lifecycle (D-01)
- TUI subscribes to EventBus events on mount (D-14) with 6 typed event handlers
- `on_submit` calls `runtime.submit_prompt()` instead of `queue_manager.enqueue()` (D-15 non-blocking)
- StatusBar widget gained `update_processing()` and `update_last_result()` methods
- StatusBar retains `update_status()` for backward compatibility with worker/repl mode
- All 34 existing tests continue to pass

## Task Commits

Each task was committed atomically:

1. **task 1: refactor TUI constructor and remove worker lifecycle** - `3bb121f` (feat)
2. **task 2: update StatusBar widget with processing/result display** - `95d5dba` (feat)

## Files Created/Modified

- `tui/app.py` - Refactored from QueueManager-driven worker pattern to RuntimeAPI event consumer (130 lines, +29 net)
- `tui/widgets/status_bar.py` - Added `_processing`/`_last_result` fields, `update_processing()`, `update_last_result()`; retained legacy `update_status()`

## Decisions Made

- `on_row_selected` adapted to extract data directly from grid row values instead of QueueManager lookup — the job queue is no longer managed by the TUI
- EventBus imported from `harness.event_bus` rather than through `harness.__init__` for explicit dependency path
- `update_status()` retained with deprecation note in StatusBar for worker/repl backward compat until Plan 05-07 refactors those callers

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 2 - Missing Critical] on_row_selected no longer has QueueManager to look up job details**
- **Found during:** task 1 (refactoring tui/app.py)
- **Issue:** The plan said to "RETAIN unchanged" `on_row_selected`, but it referenced `self._manager.get_job()` which was removed with QueueManager. Would crash at runtime.
- **Fix:** Adapted `on_row_selected` to extract job ID and prompt directly from the DataTable row values, passing `None` for result/error since the Runtime doesn't manage job queue results in interactive mode.
- **Files modified:** tui/app.py
- **Verification:** Method now works with available data; no crash path from removed `self._manager`.
- **Committed in:** 3bb121f (task 1 commit)

**2. [Plan inconsistency] File size estimate (80-90 lines) vs actual (130 lines)**
- **Found during:** task 1 (refactoring tui/app.py)
- **Issue:** Plan stated final app.py should be "~80-90 lines (shorter than current 101 lines)" but adding 6 event handlers (~36 lines) + _subscribe_to_events (~10 lines) + imports (~15 lines) necessarily increases total lines beyond 101. The estimate didn't account for new event handler code.
- **Fix:** No code change needed — functional correctness prioritized over line count. The file is 130 lines, which is correct for the required functionality.
- **Committed in:** 3bb121f

---

**Total deviations:** 2 auto-fixed (1 missing critical, 1 plan inconsistency)
**Impact on plan:** Both auto-fixes ensure correctness and usability. No scope creep.

## Issues Encountered

None — plan executed cleanly.

## Verification Results

```
$ python -c "import ast; ast.parse(open('tui/app.py').read()); print('tui/app.py syntax OK')"
PASS: tui/app.py syntax OK

$ python -c "import ast; ast.parse(open('tui/widgets/status_bar.py').read()); print('status_bar.py syntax OK')"
PASS: status_bar.py syntax OK

QueueManager import removed from tui/app.py: PASS
RuntimeAPI imported in tui/app.py: PASS

$ python -m pytest tests/ -x -q
34 passed in 4.43s
```

## Self-Check: PASSED

- [x] `tui/app.py` exists and is valid Python
- [x] `tui/widgets/status_bar.py` exists and is valid Python
- [x] Commit `3bb121f` exists for task 1
- [x] Commit `95d5dba` exists for task 2
- [x] No QueueManager in app.py
- [x] RuntimeAPI imported in app.py
- [x] All 34 tests pass

## Threat Flags

None — all new code stays within existing trust boundaries (in-process event handlers, no new network endpoints).

## User Setup Required

None - no external service configuration required.

## Next Phase Readiness

- TUI is now a pure view layer ready for Plan 05-07 (main.py integration)
- Plan 05-07 should refactor worker/repl mode callers still using `update_status()`
- Plan 05-07 should wire RuntimeAPI into the TUI constructor in main.py

---

*Phase: 05-harness-runtime*
*Completed: 2026-07-26*
