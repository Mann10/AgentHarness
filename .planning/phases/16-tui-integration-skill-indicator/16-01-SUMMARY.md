---
phase: 16-tui-integration-skill-indicator
plan: 01
subsystem: api
tags: [skill_loaded, notification, event-bus, json-rpc, typed-event, zustand]

# Dependency graph
requires:
  - phase: 15-session-behavior-skill-command
    provides: skills.load RPC + {skill, status} ack contract + load_skill_status
  - phase: 14-read-skill-provider-e2e
    provides: single shared RuntimeAPI.load_skill() path + __skills__ provider
provides:
  - SkillLoadedEvent + EVENT_SKILL_LOADED emitted from the shared load_skill() path only
  - NotificationType.skill_loaded (8th wire type) with {skill}-only payload extractor
  - TUI handleEvent skill_loaded case → store.addLoadedSkill (chip state only, no pollution)
  - loadedSkills/addLoadedSkill/addSkillNotice store state resetting in both reset paths
  - 9-test pytest suite covering all five automated ACT-06 dimensions
affects: [16-02-tui-input-skill, 16-03-tui-indicator-chip, 17-allowed-tools-enforcement]

# Tech tracking
tech-stack:
  added: []
  patterns:
    - Five-touchpoint typed notification extension (harness event → server mapping+extractor → protocol → handleEvent → store)
    - {skill}-only payload contract (D-06): status lives in RPC ack, never in notification
    - Dedup-append store action (belt-and-suspenders; backend is the dedup authority)

key-files:
  created:
    - tests/test_skill_loaded_notification.py
  modified:
    - harness/events.py
    - harness/runtime.py
    - harness/__init__.py
    - backend/rpc/protocol.py
    - backend/rpc/server.py
    - tui-ink/src/types.ts
    - tui-ink/src/store/agent-store.ts
    - tui-ink/src/bridge/rpc-client.ts

key-decisions:
  - "Emission point locked to load_skill() only (not load_skill_status) — covers both read_skill and /skill activation paths with zero double-fire"
  - "SkillLoadedEvent carries session_id on the dataclass (wire request_id consistency) but payload extractor returns {skill} only (D-06)"
  - "handleEvent skill_loaded case touches ONLY addLoadedSkill — no notice, no status/busy, no stream message (ROADMAP criterion 4)"
  - "loadedSkills: [] reset in BOTH resetConversation and loadConversation (D-09) — setActiveSession is not a reset"

patterns-established:
  - "Extension checklist for an 8th notification type: dataclass+constant → import+mapping+extractor+subscribe → enum member → switch case → store state"
  - "TDD split for cross-language contract: backend touchpoints pytest-automatable, TUI touchpoints verified by typecheck (no TS test runner — Phase 11 precedent)"

requirements-completed: [ACT-06]

# Metrics
duration: 7min
completed: 2026-08-03
---

# Phase 16 Plan 1: skill_loaded Notification Contract Summary

**Typed `skill_loaded` notification wired through all five touchpoints of the D-09 pipeline — `SkillLoadedEvent` emitted from the shared `load_skill()` path (user and model activation alike), `{skill}`-only payload extractor on the server, 8th `NotificationType` member, `handleEvent` case driving `addLoadedSkill` chip state, and a 9-test pytest suite proving emission, no-op silence, exact wire format, RPC round trip, and zero stream pollution.**

## Performance

- **Duration:** 7 min
- **Started:** 2026-08-03T21:16:26Z
- **Completed:** 2026-08-03T21:23:51Z
- **Tasks:** 3 (2 TDD: RED → GREEN, 1 TUI contracts)
- **Files modified:** 9 (1 created, 8 modified)

## Accomplishments

- `SkillLoadedEvent` + `EVENT_SKILL_LOADED` in `harness/events.py`, barrel-exported through `harness/__init__.py`; emitted in `runtime.load_skill()` strictly after `add_skill_message` — zero events on `already_loaded`/not_found/cap-refusal (T-16-01 mitigated, D-07)
- `NotificationType.skill_loaded` as the 8th wire type; `_DOMAIN_TO_NOTIFICATION` mapping, `_extract_skill_loaded_payload` returning `{"skill": event.skill}` only (T-16-02 mitigated, D-06), registered in `_PAYLOAD_EXTRACTORS`, subscribed in `start()` / unsubscribed in `shutdown()`
- TUI contracts: `SkillLoadedPayload` + `EventPayload` union member + `Message.tone` + `AgentState.loadedSkills` in types.ts (Pitfall 3 avoided); `addLoadedSkill` dedup-append + `addSkillNotice` (never touches status/busy/error — `addError` not reused, Pitfall 5) + `loadedSkills: []` in BOTH reset paths (Pitfall 1 avoided, D-09); `handleEvent` `skill_loaded` case calling `addLoadedSkill(p.skill)` only (Pitfall 7 avoided, ROADMAP criterion 4)
- 9-test pytest suite in `tests/test_skill_loaded_notification.py` covering all five automated ACT-06 dimensions with `-k` filters locked by 16-VALIDATION.md

## Task Commits

Each task was committed atomically:

1. **Task 1: Wave 0 test scaffold (RED)** - `617a071` (test)
2. **Task 2: Backend implementation (GREEN)** - `cd40062` (feat)
3. **Task 3: TUI contracts** - `bdcb72a` (feat)

**Plan metadata:** `(pending — committed after SUMMARY creation)`

_Note: Tasks 1-2 followed TDD RED → GREEN; task 3 is contract-only work verified by typecheck._

## Files Created/Modified

- `tests/test_skill_loaded_notification.py` - 9 tests: `-k "emits"` (both activation paths), `-k "no_event"` (already_loaded/not_found/cap-refusal), `-k "wire_format"` (exact dict + skill-only payload), `-k "round_trip"` (skills.load dispatcher → response + independent notification), `-k "pollution"` (system-only body)
- `harness/events.py` - `SkillLoadedEvent` dataclass (session_id + skill) + `EVENT_SKILL_LOADED = "SkillLoadedEvent"` (name == class name, EventBus routing)
- `harness/runtime.py` - `from harness.events import SkillLoadedEvent`; emission between `add_skill_message` (line 212) and the return (line 213) in `load_skill`
- `harness/__init__.py` - `SkillLoadedEvent` + `EVENT_SKILL_LOADED` in import block and `__all__`
- `backend/rpc/protocol.py` - `skill_loaded = "skill_loaded"` as 8th `NotificationType` member
- `backend/rpc/server.py` - import both symbols; mapping entry; `_extract_skill_loaded_payload`; extractor registration; subscribe/unsubscribe in start()/shutdown()
- `tui-ink/src/types.ts` - `SkillLoadedPayload { skill }`, `EventPayload` union member, `Message.tone?: "success" | "error"`, `AgentState.loadedSkills: string[]`
- `tui-ink/src/store/agent-store.ts` - `loadedSkills: [] as string[]` initial state; `addLoadedSkill` (dedup-append); `addSkillNotice` (never touches status/busy/error); `loadedSkills: []` in `resetConversation` + `loadConversation`
- `tui-ink/src/bridge/rpc-client.ts` - `case "skill_loaded"` in `handleEvent` after `cancelled`: `const p = payload as { skill: string }; store.addLoadedSkill(p.skill)`

## Decisions Made

- **Emission in `load_skill`, not `load_skill_status`** — `load_skill_status` dedup-checks then delegates; a second emission point would double-fire. Single emission in the shared path covers both RPC and `read_skill` (research anti-pattern avoided).
- **`session_id` on the event, not in the payload** — carried for wire `request_id` consistency (matches every other event); extractor enforces D-06 `{skill}`-only.
- **`handleEvent` case is chip-only** — `addLoadedSkill` is the sole call; notices come exclusively from the `/skill` RPC ack path (16-02), never from the notification.
- **Store reset in both reset paths** — `loadedSkills: []` in `resetConversation` (the `/new` path) AND `loadConversation` (session-switch path); `setActiveSession` only sets the id.

## Deviations from Plan

None - plan executed exactly as written.

## Issues Encountered

None - all grep gates, pytest, and typecheck passed on first verification pass.

## TDD Gate Compliance

- RED gate: `617a071 test(16-01): add failing test for skill_loaded notification` — tests failed with the expected `ImportError: cannot import name 'EVENT_SKILL_LOADED'` before any implementation
- GREEN gate: `cd40062 feat(16-01): implement skill_loaded notification backend` — all 9 tests pass
- REFACTOR gate: N/A (no refactor needed — implementation minimal per plan)
- Gate sequence compliant: no violations

## User Setup Required

None - no external service configuration required.

## Next Phase Readiness

- **16-02 (InputBar `/skill` intercept):** ready — `loadSkill()` client method and `SkillLoadResult`/`SkillLoadStatus` types already exist; `addSkillNotice` action with tone is now available for outcome notices; the `skills.load` ack `{skill, status}` contract is the notice source
- **16-03 (Footer chip + notice rendering):** ready — `loadedSkills` store state consumed by the future chip, `Message.tone` drives notice variants; chip updates arrive via the notification (this plan's contract), notices via the ack
- **Backend consumers:** REPL and TUI both get the typed event from the shared path — no per-consumer drift

---

*Phase: 16-tui-integration-skill-indicator*
*Completed: 2026-08-03*

## Self-Check: PASSED

- [x] `tests/test_skill_loaded_notification.py` exists on disk
- [x] `16-01-SUMMARY.md` exists on disk
- [x] Commit `617a071` (RED test) exists in git history
- [x] Commit `cd40062` (GREEN backend) exists in git history
- [x] Commit `bdcb72a` (TUI contracts) exists in git history
- [x] `python -m pytest tests/test_skill_loaded_notification.py -x` — 9 passed
- [x] `python -m pytest -q` — 191 passed, 1 skipped (no regressions)
- [x] `npm run typecheck` — 0 errors
- [x] `npm run build` — build success
