---
phase: 15-session-behavior-skill-command
plan: 01
subsystem: api
tags: [json-rpc, skills, rpc, typescript, tdd]

# Dependency graph
requires:
  - phase: 14-read-skill-provider-e2e
    provides: RuntimeAPI.load_skill shared path, SkillStore, skill_state["loaded"] exactly-once dedup (H-01)
provides:
  - skills.load JSON-RPC method whitelisted in RPC_METHODS with SKILL_NOT_FOUND domain code
  - Dispatcher RPCError passthrough (structured D-08 codes reach clients instead of -32603)
  - RuntimeAPI.load_skill_status structured {skill, status} method reusing load_skill (D-07)
  - TS SkillLoadResult contract + loadSkill() client method for Phase 16
affects: [16-tui-integration, 15-02, 15-03]

# Tech tracking
tech-stack:
  added: []
  patterns:
    - "JSON-RPC domain error codes (D-08): handler raises RPCError, dispatcher passes code/message through verbatim"
    - "4-layer contract mirror (protocol → adapter → rpc-client → types) for skills.load"
    - "RPCError subclasses Exception (dataclass exception) so handlers can raise structured errors"

key-files:
  created:
    - tests/test_skills_load_rpc.py
  modified:
    - backend/rpc/protocol.py
    - backend/rpc/__init__.py
    - backend/rpc/dispatcher.py
    - backend/rpc/adapter.py
    - harness/runtime.py
    - tui-ink/src/types.ts
    - tui-ink/src/bridge/rpc-client.ts

key-decisions:
  - "RPCError made a dataclass Exception so D-08 raise/except contract works (deviation)"
  - "SKILL_NOT_FOUND = -32001 domain code, exported from backend.rpc"
  - "except RPCError clause placed BEFORE generic except Exception in Dispatcher.dispatch"
  - "load_skill_status reuses load_skill() (D-07 single shared path), dedups by canonical name (H-01)"
  - "TS contract-only this plan — TUI UI/notification deferred to Phase 16"

patterns-established:
  - "RPC domain errors: raise RPCError(code, message) in adapter, catch in dispatcher before -32603 wrap"

requirements-completed: [ACT-01]

# Metrics
duration: 5min
completed: 2026-08-02
---

# Phase 15 Plan 01: skills.load RPC Contract — Summary

**Full 4-layer `skills.load` JSON-RPC method (protocol whitelist → dispatcher RPCError passthrough → adapter handler → runtime status method) plus the TS `SkillLoadResult` contract and `loadSkill()` client method, delivered test-first with structured D-08 error codes (-32602 / -32001) instead of generic -32603 failures**

## Performance

- **Duration:** 5 min
- **Started:** 2026-08-02T20:14:17Z
- **Completed:** 2026-08-02T20:19:50Z
- **Tasks:** 3
- **Files modified:** 8

## Accomplishments
- `skills.load` whitelisted in `RPC_METHODS` (D-05) and registered in `register_all()` (9 existing + 1 = 10 methods) — verified by tests
- Dispatcher now passes `RPCError` codes through verbatim (D-08) before the generic -32603 wrap; unknown exceptions still wrap as -32603 (regression test)
- `handle_skills_load` validates name (INVALID_PARAMS) and maps unknown skills to `SKILL_NOT_FOUND` (-32001) with the skill named in the message
- `RuntimeAPI.load_skill_status` returns `{skill, status}` with no body echo (D-06), reusing `load_skill` shared path (D-07) with canonical-name dedup (H-01)
- TS `SkillLoadResult` type + `loadSkill()` client method type-check cleanly — the Phase 16 TUI contract
- 9 new tests (TDD RED→GREEN), full suite green: 165 passed, 1 skipped

## task Commits

Each task was committed atomically:

1. **task 1: Wave 0 — create tests/test_skills_load_rpc.py (RED scaffold)** - `0103495` (test)
2. **task 2: Backend — protocol whitelist, dispatcher passthrough, runtime load_skill_status, adapter handler (GREEN)** - `0413bf3` (feat)
3. **task 3: TS contract — SkillLoadResult type + loadSkill() client method** - `60dfdc7` (feat)

**Plan metadata:** `pending` (docs commit after SUMMARY)

## Files Created/Modified
- `tests/test_skills_load_rpc.py` - 9 tests: whitelist, SKILL_NOT_FOUND code, RPCError passthrough, -32603 regression, INVALID_PARAMS, SKILL_NOT_FOUND mapping, loaded status, register_all registration, already_loaded dedup (real RuntimeAPI fixture)
- `backend/rpc/protocol.py` - `"skills.load"` in RPC_METHODS; `SKILL_NOT_FOUND = -32001`; RPCError now subclasses Exception
- `backend/rpc/__init__.py` - exports SKILL_NOT_FOUND alongside RPC_METHODS
- `backend/rpc/dispatcher.py` - `except RPCError` passthrough clause before generic `except Exception`
- `backend/rpc/adapter.py` - `handle_skills_load` handler + `skills.load` registration; imports RPCError/INVALID_PARAMS/SKILL_NOT_FOUND; register_all docstring updated to "all 10 RPC methods"
- `harness/runtime.py` - `load_skill_status(name) -> dict` structured method next to `load_skill`
- `tui-ink/src/types.ts` - `SkillLoadStatus` union + `SkillLoadResult` interface
- `tui-ink/src/bridge/rpc-client.ts` - `loadSkill(name)` method + `SkillLoadResult` import

## Decisions Made
- **RPCError as dataclass Exception:** D-08 requires handlers to `raise RPCError(...)` and the dispatcher to `except RPCError`. The existing RPCError was a plain `@dataclass` (not an exception), so raising/catching was impossible (`TypeError: exceptions must derive from BaseException`). Made it `@dataclass class RPCError(Exception)` — serialization via `asdict` in server.py is unaffected (still a dataclass). This was a Rule 1/3 auto-fix (see Deviations).
- **SKILL_NOT_FOUND = -32001** (D-08 domain code, per research §1), exported from `backend.rpc`.
- **`except RPCError` placed BEFORE generic `except Exception`** in `Dispatcher.dispatch()` — additive, existing handlers never raise RPCError so behavior unchanged.
- **load_skill_status delegates to load_skill()** (D-07) — no drift between REPL/TUI/model-driven activation; status derived from pre-call `skill_state["loaded"]` membership (canonical name, H-01).
- **TS contract-only this plan** — no TUI UI, notification wiring, or store changes (deferred to Phase 16 per 15-CONTEXT).

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 1/3 - Bug/Blocking] RPCError is not an exception class — D-08 raise/except contract impossible**
- **Found during:** task 2 (GREEN test run)
- **Issue:** The plan's design (and its own code shapes) requires `raise RPCError(...)` in the adapter and `except RPCError` in the dispatcher, but the existing `RPCError` was a plain `@dataclass` not deriving from `BaseException`. All 4 RPCError-related tests failed with `TypeError: exceptions must derive from BaseException` / `catching classes that do not inherit from BaseException is not allowed`.
- **Fix:** Changed `RPCError` to inherit from `Exception` (`@dataclass class RPCError(Exception)`). All existing constructor/`asdict` usage is preserved; `server.py` serialization unaffected.
- **Files modified:** backend/rpc/protocol.py
- **Verification:** `python -m pytest tests/test_skills_load_rpc.py tests/test_rpc_adapter.py tests/test_load_skill.py -q` → 26 passed; full suite 165 passed, 1 skipped
- **Committed in:** 0413bf3 (task 2 commit)

---

**Total deviations:** 1 auto-fixed (1 bug/blocking)
**Impact on plan:** The fix was required for the plan's D-08 design to function at all — no scope creep. Without it, structured error codes could not reach RPC clients.

## Issues Encountered
- **RED-stage `--co` collection:** Task 1's acceptance criterion "`pytest --co -q` collects the file without syntax errors" cannot literally pass at RED time — the file imports `SKILL_NOT_FOUND`, which doesn't exist yet, so `--co` reports an ImportError during collection (the same expected RED failure, not a syntax error). After task 2 (GREEN), `--co` collects cleanly and the full run passes. This is inherent to the plan's RED scaffold design, not a code defect.

## User Setup Required

None - no external service configuration required.

## Next Phase Readiness
- The `skills.load` contract spans all 4 layers and is fully tested — Phase 16 can build the TUI input-bar intercept, "Skill loaded" indicator, and `skill_loaded` notification directly on `loadSkill()` + `SkillLoadResult`.
- Plan 15-02 (`/skill` REPL command) consumes `runtime.load_skill()` directly (D-07) — no dependency on this plan's RPC surface, but shares the same `load_skill`/dedup path.
- Threat register dispositions T-15-01..T-15-05 all mitigated by the implementation and covered by tests.

---
*Phase: 15-session-behavior-skill-command*
*Completed: 2026-08-02*

## Self-Check: PASSED

- FOUND: tests/test_skills_load_rpc.py
- FOUND: backend/rpc/protocol.py
- FOUND: backend/rpc/dispatcher.py
- FOUND: backend/rpc/adapter.py
- FOUND: harness/runtime.py
- FOUND: tui-ink/src/types.ts
- FOUND: tui-ink/src/bridge/rpc-client.ts
- FOUND: 15-01-SUMMARY.md
- FOUND commit: 0103495 (test, RED gate)
- FOUND commit: 0413bf3 (feat, GREEN gate)
- FOUND commit: 60dfdc7 (feat, TS contract)
