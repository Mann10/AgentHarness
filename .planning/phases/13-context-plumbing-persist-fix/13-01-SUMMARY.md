---
phase: 13-context-plumbing-persist-fix
plan: 01
subsystem: session-persistence
tags: [persist, message, dataclass, session-memory, skills, ACT-03]

# Dependency graph
requires:
  - phase: 12-skills-discovery-and-manifest
    provides: SkillInfo, frontmatter parser, one-pass discovery, Session.skill_manifest system-prompt seam
provides:
  - "Message.persist flag — the datum-level contract for skill-body exemptness from JSONL serialization"
  - "tests/test_persist.py — Wave 0 contract test scaffold for the phase (every later plan appends here)"
affects: [13-02 (Session.to_events persist filter), 13-03 (mark_saved/unpersisted_events index), 14-read_skill-provider-end-to-end, 15-session-behavior-and-skill-command]

# Tech tracking
tech-stack:
  added: []
  patterns:
    - "Datum-level persist flag: Message.persist defaults True so every existing construction site (agent/core.py, context.py, tests) is backward compatible; only skill-body injection constructs persist=False"

key-files:
  created: [tests/test_persist.py]
  modified: [context/message.py]

key-decisions:
  - "Message.persist defaults True — backward compatibility is proven, not assumed (all 103 pre-existing tests pass unchanged)"
  - "Message.from_dict does NOT read a persist key — stored events never carry the key and are persisted by definition"
  - "persist=False is reserved for Phase 14's add_skill_message() skill-body injection"

patterns-established:
  - "persist-flag convention: a boolean opt-out on the datum level, defaults to persist (safe default for session memory)"

requirements-completed: [ACT-03]

# Metrics
duration: 1min
completed: 2026-08-01
---

# Phase 13 Plan 01: Message.persist Datum-Level Contract Summary

**`Message.persist` field (default True) added to `context/message.py` as the datum-level contract for skill-body exemptness from JSONL serialization, with a 4-test contract suite (`tests/test_persist.py`) proving backward compatibility — every existing caller and all 103 pre-existing tests keep working unchanged (ACT-03).**

## Performance

- **Duration:** 1 min
- **Started:** 2026-08-01T20:04:16Z
- **Completed:** 2026-08-01T20:05:16Z
- **Tasks:** 2
- **Files modified:** 2

## Accomplishments

- `Message.persist: bool = True` added as the last dataclass field (after `tool_call_id`) — safe default means agent turns, store round-trips, and summarization all work unchanged
- `Message.from_dict` deliberately does NOT read a `persist` key — stored JSONL events never carry the key and are persisted by definition
- New `tests/test_persist.py` contract suite (4 tests): default persist, explicit `persist=False`, `from_dict` compat, and LLM visibility of a persist=False system message — the Wave 0 scaffold every later Phase 13 plan appends to
- Full suite green at 107 tests (103 existing + 4 new) — backward compatibility proven, not assumed

## task Commits

Each task was committed atomically:

1. **task 1: RED — write contract tests for Message.persist** - `412038d` (test)
2. **task 2: GREEN — implement Message.persist field** - `9515bed` (feat)

**Plan metadata:** (created below with this SUMMARY.md commit)

## Files Created/Modified

- `context/message.py` - Added `persist: bool = True` as last dataclass field; `from_dict` unchanged (never reads the persist key)
- `tests/test_persist.py` - New contract suite: default persist, explicit opt-out, from_dict compat, to_llm_messages visibility (ACT-03)

## Decisions Made

- `Message.persist` defaults True — backward compat proven by 103 pre-existing tests passing unchanged
- `Message.from_dict` ignores a `persist` key — stored events always persist=True (research pitfall: "stored events should never carry the key")
- `persist=False` is reserved for Phase 14's `add_skill_message()` — skill-body injection is the only construction site that opts out

## Deviations from Plan

None - plan executed exactly as written.

## Issues Encountered

None.

## User Setup Required

None - no external service configuration required.

## Next Phase Readiness

- Plan 13-02 can build `Session.to_events()` persist filtering (T-13-01 mitigation) and `mark_saved`/`unpersisted_events` indexing (T-13-02) on the `Message.persist` flag
- Phase 14's `add_skill_message()` has its opt-out hook ready: `Message(role="system", content=body, persist=False)`
- Test scaffold `tests/test_persist.py` is the append target for guard tests asserting JSONL never contains skill content

## TDD Gate Compliance

- RED gate: `412038d` — `test(13-01): add failing contract tests for Message.persist` (failed with `AttributeError: 'Message' object has no attribute 'persist'` before any implementation)
- GREEN gate: `9515bed` — `feat(13-01): implement Message.persist field` (all 4 contract tests + full suite pass)
- REFACTOR gate: not applicable — implementation was a single-field addition, no cleanup needed

## Self-Check: PASSED

- FOUND: `context/message.py` — contains `persist: bool = True` (last field)
- FOUND: `tests/test_persist.py` — 4 contract tests, all green
- FOUND: `13-01-SUMMARY.md`
- FOUND: commit `412038d` (RED gate), commit `9515bed` (GREEN gate)

---
*Phase: 13-context-plumbing-persist-fix*
*Completed: 2026-08-01*
