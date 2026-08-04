---
phase: 13-context-plumbing-persist-fix
plan: 02
subsystem: session-persistence
tags: [persist, jsonl, to-events, index-drift, round-trip, ACT-05, D-13]

# Dependency graph
requires:
  - phase: 13-context-plumbing-persist-fix
    plan: 01
    provides: Message.persist datum-level flag (default True) + tests/test_persist.py scaffold
provides:
  - "Session.to_events() persist filter — persist=False messages never reach the JSONL projection (D-13 leak closed)"
  - "Session.mark_saved() persisted-count index — repeated saves produce no missing/duplicated events (index-drift closed)"
  - "Round-trip proof suite (tests 5-8): JSONL-clean save, resumed-session absence, repeated-save stability, index-shift guard"
affects: [13-03 (remaining context-plumbing plan), 14-read-skill-provider-end-to-end, 15-session-behavior-and-skill-command]

# Tech tracking
tech-stack:
  added: []
  patterns:
    - "Serialization-projection filter: to_events() is the single gate between session memory and JSONL — persist=False skips, to_llm_messages() never filters"
    - "Index alignment contract: _last_saved_count must count the same population to_events() emits (persisted messages only)"

key-files:
  created: []
  modified:
    - session/models.py
    - tests/test_persist.py

key-decisions:
  - "to_events() skips persist=False messages at loop top — one change point keeps both store.save() branches (append + full rewrite) clean"
  - "mark_saved() counts persisted messages only — closes the index drift that a naive filter would introduce"
  - "restore_context() left untouched — len(_stored_events) already counts persisted events and aligns with the new filter"
  - "No refactor commit — GREEN was already minimal (2-line filter + 1-line index)"

patterns-established:
  - "persist-flag convention: a boolean opt-out on the datum level, defaults to persist (safe default for session memory)"

requirements-completed: [ACT-05]

# Metrics
duration: 2min
completed: 2026-08-01
---

# Phase 13 Plan 02: Persist Filter + Index Fix Summary

**`Session.to_events()` now skips `persist=False` messages (skill bodies never reach the JSONL session file — D-13 leak closed) and `mark_saved()` counts persisted messages only (index-drift closed), proven by a 4-test round-trip suite: JSONL-clean save, resumed-session absence, no duplicate events on repeated saves, and no index shift for mid-stream persist=False injection (ACT-05).**

## Performance

- **Duration:** 2 min
- **Started:** 2026-08-01T20:08:23Z
- **Completed:** 2026-08-01T20:09:37Z
- **Tasks:** 2 (TDD RED + GREEN)
- **Files modified:** 2

## Accomplishments

- `Session.to_events()` (session/models.py) adds `if not msg.persist: continue` as the first loop statement — the T-13-01 mitigation (Information Disclosure): persist=False messages never appear in the JSONL projection, covering both `save()` branches (new-file write and full rewrite) plus the append path via `unpersisted_events()`
- `Session.mark_saved()` (session/models.py) now sets `_last_saved_count = sum(1 for m in self._context._messages if m.persist)` — the T-13-02 mitigation (Tampering/index integrity): the index counts the same population `to_events()` emits, so repeated saves append exactly the new persisted events
- `restore_context()` deliberately untouched — `len(self._stored_events)` counts stored (persisted) events and stays aligned with the new filter (verified by test 6)
- Four round-trip tests appended to `tests/test_persist.py` (tests 5-8): JSONL-clean save, resumed-session absence, no duplicate events on consecutive saves, no index shift for persist=False injected between saves
- Full suite green at **111 tests** (103 pre-existing + 8 persist tests) — no regressions

## task Commits

Each task was committed atomically:

1. **task 1: RED — round-trip tests for the persist filter** - `03f81ff` (test)
2. **task 2: GREEN — persist filter + index fix** - `1a30030` (feat)

**Plan metadata:** `docs(13-02)` (created below with this SUMMARY.md commit)

_Note: TDD plan — 2 commits (RED → GREEN). REFACTOR not applicable (GREEN was already minimal)._

## Files Created/Modified

- `session/models.py` - `to_events()` skips `persist=False` messages; `mark_saved()` counts persisted messages only
- `tests/test_persist.py` - Appended round-trip tests 5-8 + `JSONLSessionStore(tempfile.mkdtemp())` fixture + imports

## Decisions Made

- `to_events()` is the single serialization gate — filter there, keep `to_llm_messages()` unfiltered so the model keeps seeing skill bodies (ACT-03 preserved)
- `mark_saved()` index must match what `to_events()` emits — closing the drift the naive 1:1 assumption would create
- `restore_context()` correct as-is (`len(_stored_events)` = persisted count) — no change needed

## Deviations from Plan

None - plan executed exactly as written.

## Issues Encountered

None. The RED run failed precisely on the D-13 leak assertion (`'SKILL-BODY-SECRET' is contained here` in the raw JSONL) for all four new tests, confirming the filter and index fixes were genuinely absent; GREEN closed all four with the two-line filter plus one-line index change.

## User Setup Required

None - no external service configuration required.

## Next Phase Readiness

- Plan 13-03 can build on a leak-free serialization path — skill bodies persist in memory only (system-role, summarization-exempt) and never serialize
- Phase 14's `add_skill_message()` can inject `Message(role="system", content=body, persist=False)` with guaranteed JSONL cleanliness (ACT-05 proven end-to-end)
- `tests/test_persist.py` is now the append target for any further persist/serialization guards

## TDD Gate Compliance

- RED gate: `03f81ff` — `test(13-02): add round-trip tests for persist filter` (tests 5-8 failed with skill body present in raw JSONL before any implementation)
- GREEN gate: `1a30030` — `feat(13-02): implement persist filter and index fix` (all 8 persist tests + full 111-test suite pass)
- REFACTOR gate: not applicable — implementation was two minimal edits, no cleanup needed

## Self-Check: PASSED

- FOUND: `session/models.py` — contains `if not msg.persist:` (to_events loop) and `sum(1 for m in self._context._messages if m.persist)` (mark_saved)
- FOUND: `tests/test_persist.py` — 8 tests, all green
- FOUND: commit `03f81ff` (RED gate), commit `1a30030` (GREEN gate)
- VERIFIED: `python -m pytest -q` → 111 passed

---
*Phase: 13-context-plumbing-persist-fix*
*Completed: 2026-08-01*
