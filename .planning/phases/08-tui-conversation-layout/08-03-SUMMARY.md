---
phase: 08-tui-conversation-layout
plan: 03
subsystem: tui
tags: textual, layout, stats-panel, event-handlers

# Dependency graph
requires:
  - phase: 08-tui-conversation-layout
    plan: 01
    provides: StatsPanel widget, softer dark theme, StatsPanel CSS
  - phase: 08-tui-conversation-layout
    plan: 02
    provides: MessageCard background CSS for message bifurcation
provides:
  - Header removed from compose (D-01: no persistent header bar)
  - Split layout: main-content wraps ConversationView (1fr) + StatsPanel (30ch)
  - Stats tracking wired: token count from session.context.total_tokens, response time from event timestamps
  - Bottom bar preserved with tool-indicator, job-indicator, InputBar
affects:
  - 09-tui-session-picker
  - main.py (stats panel data flow)

# Tech tracking
tech-stack:
  added: []
  patterns:
    - Event handler stats tracking via TurnStarted.timestamp and ResponseComplete
    - StatsPanel update methods called synchronously from async event handlers

key-files:
  created:
    - tests/test_tui_layout.py — Layout structure tests
  modified:
    - tui/app.py — Header removal, split layout, stats wiring, constructor model_name parameter
    - tui/widgets/__init__.py — StatsPanel export

key-decisions:
  - "Model name passed to AgentHarnessTUI constructor rather than read from config in compose"
  - "Session name refreshed on every TurnStarted to catch session-switch updates"
  - "Response time computed as wall-clock difference between TurnStarted.timestamp and now on ResponseComplete"

patterns-established:
  - "StatsPanel updates: _update_stats_panel_session() for session/model, _update_stats_panel_after_response() for tokens/time"
  - "Turn timing: capture _turn_start_time from event.timestamp, compute elapsed on ResponseComplete"

requirements-completed:
  - D-01
  - D-02
  - D-03
  - D-04
  - D-06

# Metrics
duration: 5 min
completed: 2026-07-27
---

# Phase 8 Plan 3: Layout Restructure + Stats Wiring Summary

**Header removed, split layout (conversation + stats panel) with wired stats tracking (token count, response time, session name, model name)**

## Performance

- **Duration:** 5 min
- **Started:** 2026-07-27T18:11:00Z
- **Completed:** 2026-07-27T18:14:17Z
- **Tasks:** 3
- **Files modified:** 3

## Accomplishments

- Header widget removed from compose() per D-01 — maximizes vertical space, no chrome
- Split layout with `Horizontal(id="main-content")` wrapping ConversationView and StatsPanel per D-03
- Bottom bar preserved with tool-indicator, job-indicator, and InputBar
- Constructor accepts `model_name: str = ""` parameter for model display
- `_turn_start_time` tracked from TurnStarted.timestamp for response timing
- `_on_turn_started` captures timing and updates session name on StatsPanel
- `_on_response_complete` updates token count (`session.context.total_tokens`) and response time (elapsed seconds)
- StatsPanel exported from `widgets/__init__.py`
- 5 layout tests: Header absence, StatsPanel presence, bottom bar, conversation view, update method existence
- All existing tests pass (no regressions)

## Task Commits

Each task was committed atomically:

1. **task 1: Write layout test scaffold** - `bb246c8` (test)
2. **task 2: Remove Header, add split layout with StatsPanel** - `7b5ed91` (feat)
3. **task 3: Wire stats tracking in event handlers** - `1ff6efc` (feat)

**Plan metadata:** (to be committed)

## Files Created/Modified

- `tests/test_tui_layout.py` — 5 async tests covering layout structure
- `tui/app.py` — Restructured compose() with no Header, split layout, stats tracking helpers and wiring
- `tui/widgets/__init__.py` — Added StatsPanel to exports

## Decisions Made

- **Model name from constructor** — `AgentHarnessTUI.__init__` accepts `model_name` parameter rather than reading config directly, keeping the TUI decoupled from config access
- **Session name on every TurnStarted** — Refresh session name on each turn to catch session picker switches without needing a separate session-switch event subscription
- **Wall-clock response timing** — Response time computed from TurnStarted.timestamp to `datetime.now(timezone.utc)` on ResponseComplete, rather than using event creation timestamps (avoids event bus dispatch latency skew)

## Deviations from Plan

None - plan executed exactly as written.

## Issues Encountered

None.

## Next Phase Readiness

- Phase 8 layout complete: Theme foundation (01), Message bifurcation (02), Layout + stats wiring (03)
- Ready for Phase 08 wrap-up and next steps
- No external service configuration required

---

*Phase: 08-tui-conversation-layout*
*Completed: 2026-07-27*
