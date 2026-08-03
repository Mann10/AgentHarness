---
phase: 05-harness-runtime
plan: 01
subsystem: runtime
tags: events, event-bus, cancellation, asyncio, pub-sub

# Dependency graph
requires:
  - phase: 02-session-module
    provides: dataclass patterns and async conventions
  - phase: 04-textual-tui-and-queue
    provides: async/await patterns, asyncio primitives usage
provides:
  - Typed event dataclasses (6 event types) for Agent lifecycle observation
  - Async EventBus for decoupled pub/sub event distribution
  - CancellationToken for cooperative turn cancellation
affects:
  - 05-harness-runtime (plan 02: Scheduler)
  - 05-harness-runtime (plan 03: RuntimeAPI)
  - 05-harness-runtime (plan 04: TUI integration)

# Tech tracking
tech-stack:
  added:
    - Python stdlib dataclasses (field, default_factory)
    - Python stdlib asyncio (Lock, Event, gather)
    - uuid for event IDs
  patterns:
    - Typed event hierarchy with base dataclass
    - asyncio.Lock for coroutine-safe subscriber list mutations
    - asyncio.gather(return_exceptions=True) for handler error isolation
    - Boolean flag + asyncio.Event for cooperative cancellation
    - String constant event type names for subscription routing
    - Wildcard '*' subscriber pattern for loggers/monitoring

key-files:
  created:
    - harness/events.py — 6 typed event dataclasses + string constants
    - harness/event_bus.py — EventBus with subscribe/unsubscribe/publish
    - harness/cancellation.py — CancellationToken with cancel/wait/reset
  modified: []

key-decisions:
  - "Event type names use PascalCase class names as routing keys (TurnStarted, not turn_started)"
  - "Separate events.py from event_bus.py — type definitions stay importable without pulling in EventBus runtime"
  - "asyncio.gather(return_exceptions=True) for dispatch — one failing handler doesn't block others"
  - "CancellationToken is cooperative flag alongside asyncio.Task.cancel() — not a replacement"
  - "Wildcard '*' subscriber for global monitoring/logging"

patterns-established:
  - "Event subscription: bus.subscribe('TurnStarted', handler) using string class name keys"
  - "Handler isolation: exceptions logged but never propagated to publishers"
  - "Cancellation: Boolean flag + asyncio.Event — synchronous check via .cancelled, async wait via .wait()"

requirements-completed: [D-02, D-05, D-06, D-07]

# Metrics
duration: 12 min
completed: 2026-07-26
---

# Phase 5 Plan 01: Core Harness Infrastructure Summary

**Six typed event dataclasses, async EventBus with subscriber isolation, and CancellationToken with cooperative cancel/wait/reset**

## Performance

- **Duration:** 12 min
- **Started:** 2026-07-26T19:02:00Z
- **Completed:** 2026-07-26T19:14:00Z
- **Tasks:** 3
- **Files modified:** 3

## Accomplishments

- **harness/events.py** — 6 typed event dataclasses (TurnStarted, ToolCallEvent, ToolResultEvent, ResponseComplete, ErrorEvent, CancelledEvent) all extending HarnessEvent base with auto-generated event_id and UTC timestamp. 6 EVENT_* string constants for magic-string-free subscription routing.
- **harness/event_bus.py** — Async EventBus with subscribe/unsubscribe/publish pattern. asyncio.Lock for safe subscriber list mutations. asyncio.gather(return_exceptions=True) ensures one failing handler doesn't block other subscribers. Wildcard '*' subscribers for loggers.
- **harness/cancellation.py** — Cooperative CancellationToken with idempotent cancel(), synchronous cancelled property, async wait() coroutine, and reset() for reuse across turns.

## Task Commits

Each task was committed atomically:

1. **Task 1: Create harness/events.py with typed event dataclasses** - `96b3070` (feat)
2. **Task 2: Create harness/event_bus.py with EventBus class** - `f7d0538` (feat)
3. **Task 3: Create harness/cancellation.py with CancellationToken** - `af1c97d` (feat)

**Plan metadata:** _pending (final metadata commit after SUMMARY.md)_

## Files Created/Modified

- `harness/events.py` — 6 typed event dataclasses + 6 EVENT_* string constants (66 lines)
- `harness/event_bus.py` — EventBus class with subscribe/unsubscribe/publish + subscriber_count (80 lines)
- `harness/cancellation.py` — CancellationToken class with cancel/cancelled/wait/reset (46 lines)

## Decisions Made

- **Separate events.py file:** Type definitions stay clean and importable without pulling in EventBus runtime dependencies. Matches D-07's requirement for typed objects (not strings).
- **PascalCase event type names as routing keys:** `bus.subscribe("TurnStarted", handler)` rather than `bus.subscribe("turn_started", handler)`. Class names are natural unique identifiers that match `type(event).__name__`.
- **asyncio.Lock over threading.Lock:** All usage is async (single-threaded, multi-coroutine). threading.Lock would block the event loop.
- **asyncio.Event for CancellationToken wait():**, not a Condition or custom Future — zero-dependency, correct for one-shot signal semantics.
- **Idempotent cancel():** Calling cancel() multiple times is safe — second call is a no-op (event.set() is already idempotent).

## Deviations from Plan

None - plan executed exactly as written.

## Issues Encountered

None - all tasks completed without issues on first attempt.

## Verification Results

- `harness/events.py` — All 6 event types importable, TurnStarted constructible with session_id and prompt ✓
- `harness/event_bus.py` — subscribe/publish roundtrip works, error isolation verified (bad handler doesn't block good handler) ✓
- `harness/cancellation.py` — cancel(), cancelled property, wait(), reset() all work, idempotent cancel verified ✓
- All three modules importable from harness package without `__init__.py` ✓
- Project conventions: `from __future__ import annotations`, `logging`, private attrs all present ✓
- Min lines: events.py 66 (need 40), event_bus.py 80 (need 60), cancellation.py 46 (need 25) ✓
- All `must_haves` artifacts and key_links verified ✓

## User Setup Required

None - no external service configuration required.

## Next Phase Readiness

- Core event infrastructure complete — ready for Plan 02 (Scheduler and backlog queue)
- EventBus interface provides subscribe/unsubscribe/publish for Scheduler to emit events
- CancellationToken provides cancel/wait/reset for Scheduler to manage turn lifecycle
- Next plan can build Scheduler that consumes EventBus and CancellationToken

## Self-Check: PASSED

All claims verified:
- [x] `harness/events.py` exists (66 lines, contains `class TurnStarted`)
- [x] `harness/event_bus.py` exists (80 lines, contains `class EventBus`)
- [x] `harness/cancellation.py` exists (46 lines, contains `class CancellationToken`)
- [x] Commit 96b3070 exists: `feat(05-harness-runtime-01): create harness/events.py`
- [x] Commit f7d0538 exists: `feat(05-harness-runtime-01): create harness/event_bus.py`
- [x] Commit af1c97d exists: `feat(05-harness-runtime-01): create harness/cancellation.py`
- [x] All three modules importable: `from harness.events import *; from harness.event_bus import EventBus; from harness.cancellation import CancellationToken`

---

*Phase: 05-harness-runtime*
*Completed: 2026-07-26*
