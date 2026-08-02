---
phase: 15-session-behavior-skill-command
plan: 03
subsystem: api
tags: [skills, tokens, cap, limits, tdd, repl, rpc]

# Dependency graph
requires:
  - phase: 14-read-skill-provider-e2e
    provides: RuntimeAPI.load_skill shared path, SkillStore, skill_state["loaded"] exactly-once dedup (H-01)
  - phase: 15-02
    provides: /skill REPL branch in _handle_session_cmd (the D-11 RuntimeError catch slots in here)
  - phase: 15-01
    provides: handle_skills_load RPC handler + load_skill_status (the D-11 RuntimeError mapping lands here)
provides:
  - Separate loaded-skill token accounting: count_tokens at load time, cached per skill in skill_state["loaded"]["tokens"] (D-09)
  - LOADED_SKILL_TOKEN_CAP env-var cap (default 8000, D-10/D-12) via skills/limits.py loaded_skill_token_cap()
  - D-11 cap-refusal RuntimeError wired to the user in every path: REPL /skill prints str(exc) (returns True, stays alive), RPC maps to documented -32603 INTERNAL_ERROR with verbatim message, read_skill propagates as tool error
  - CAP-04 combined-filter semantics as pure unit-tested intersect_allowed_tools() (D-13 intersection, D-14 empty-set skip) + docs/skills-allowed-tools.md decision record for Phase 17
affects: [16-tui-integration, 17-allowed-tools-enforcement]

# Tech tracking
tech-stack:
  added: []
  patterns:
    - "Env-var configurable cap: skills/limits.py loaded_skill_token_cap() mirrors skills/manifest.py manifest_max_chars() exactly"
    - "Mark-before-inject (H-03): cap check precedes the skill_state append so a refused load leaves no partial state"
    - "e.get('tokens', 0) tolerates legacy name/dir-only records — mixed-shape skill_state data sums safely"
    - "Contract-before-enforcement: intersect_allowed_tools() + retain_read_skills() are pure unit-tested contracts; enforcement wiring is Phase 17"

key-files:
  created:
    - skills/limits.py
    - docs/skills-allowed-tools.md
    - tests/test_skills_filter.py
  modified:
    - harness/runtime.py
    - skills/filter.py
    - skills/__init__.py
    - main.py
    - backend/rpc/adapter.py
    - tests/test_load_skill.py
    - tests/test_skill_command.py
    - tests/test_skills_load_rpc.py

key-decisions:
  - "D-11 cap-refusal RuntimeError reaches every user path: REPL /skill prints str(exc) and returns True; RPC maps to documented -32603 INTERNAL_ERROR with verbatim message (message string IS the contract, no dedicated domain code); read_skill propagates as tool error"
  - "Cap check placed BEFORE the skill_state append (H-03 mark-before-inject) — refused loads leave no partial state"
  - "Token count cached as 'tokens' in skill_state['loaded'] records (D-09); e.get('tokens', 0) keeps legacy name/dir records summable"
  - "intersect_allowed_tools() shipped as pure unit-tested contract (D-13/D-14); enforcement deferred to Phase 17 per ROADMAP criterion 4"
  - "D-12 default cap 8000 tokens, env-overridable via LOADED_SKILL_TOKEN_CAP (mirrors SKILL_MANIFEST_MAX_CHARS pattern)"

patterns-established:
  - "Cap functions: module-level env-resolved function with default + non-numeric/non-positive fallback (manifest.py precedent)"
  - "REPL error surfacing: except RuntimeError in _handle_session_cmd branch prints str(exc) so run_repl never tracebacks"

requirements-completed: [ACT-01]

# Metrics
duration: 5min
completed: 2026-08-02
---

# Phase 15 Plan 03: Loaded-Skill Token Cap + CAP-04 Contract — Summary

**Separate loaded-skill token accounting with an env-configurable cap (LOADED_SKILL_TOKEN_CAP, default 8000) cached per skill in skill_state["loaded"], D-11 cap-refusal RuntimeError surfaced in every user path (REPL /skill prints str(exc), RPC maps to documented -32603 with the verbatim message), plus the CAP-04 intersection semantics shipped as a pure unit-tested `intersect_allowed_tools()` with a decision doc for Phase 17**

## Performance

- **Duration:** 5 min
- **Started:** 2026-08-02T16:09:00Z
- **Completed:** 2026-08-02T16:14:23Z
- **Tasks:** 3
- **Files modified:** 10

## Accomplishments
- `skills/limits.py` — `loaded_skill_token_cap()`: `LOADED_SKILL_TOKEN_CAP` env var, default 8000 tokens (D-10/D-12), non-numeric/non-positive fallback mirroring `manifest_max_chars`
- `harness/runtime.py` `load_skill()` — counts the body via `client.count_tokens()` at load (D-09), caches it in the `skill_state["loaded"]` record (`tokens` field), refuses the load with a clear cap-naming RuntimeError when the combined total would exceed the cap (D-11), check placed BEFORE the append (H-03 mark-before-inject — no partial state, no body injection)
- D-11 refusal reaches the user in EVERY path: REPL `/skill` prints `str(exc)` and returns True (REPL stays alive — no traceback), RPC `handle_skills_load` maps RuntimeError → `RPCError(INTERNAL_ERROR=-32603, message=str(exc))` with the verbatim D-11 message, and `read_skill` keeps propagating it as a tool error
- CAP-04 semantics locked: `intersect_allowed_tools()` pure function (D-13 intersection over restricted skills only, D-14 empty `allowed_tools` = no restriction) + `docs/skills-allowed-tools.md` decision record for the Phase 17 planner
- Chat tokens stay separate from loaded-skill tokens — summarization threshold remains chat-relative (ROADMAP criterion 3)
- 11 new tests (RED→GREEN), full suite green: 182 passed, 1 skipped (was 171 + 1)

## task Commits

Each task was committed atomically:

1. **task 1: Wave 0 — create tests/test_skills_filter.py + extend test_load_skill/test_skill_command/test_skills_load_rpc (RED scaffold)** - `ad42b36` (test)
2. **task 2: Implement loaded_skill_token_cap + token accounting + cap refusal in load_skill + D-11 REPL/RPC wiring (GREEN)** - `3c1be7d` (feat)
3. **task 3: Implement intersect_allowed_tools (CAP-04 contract) + decision doc (GREEN)** - `c94dd7d` (feat)

## Files Created/Modified
- `skills/limits.py` - NEW: `loaded_skill_token_cap()` env-var cap function (D-10/D-12)
- `harness/runtime.py` - `load_skill()`: count_tokens at load (D-09), cap refusal before append (D-11/H-03), `tokens` field in loaded records
- `skills/filter.py` - NEW `intersect_allowed_tools()` pure function (D-13/D-14)
- `skills/__init__.py` - barrel exports: `loaded_skill_token_cap`, `intersect_allowed_tools`
- `main.py` - `/skill` branch: `except RuntimeError` prints `str(exc)` after `except KeyError`
- `backend/rpc/adapter.py` - `handle_skills_load`: `except RuntimeError` → `RPCError(INTERNAL_ERROR, message=str(exc))`; INTERNAL_ERROR import added
- `docs/skills-allowed-tools.md` - NEW: CAP-04 decision record (D-13/D-14/CAP-03) + Phase 17 enforcement plan
- `tests/test_skills_filter.py` - NEW: 6 tests for the intersection contract (empty-set skip, single, disjoint, all-unrestricted, empty input)
- `tests/test_load_skill.py` - 3 new tests: token record shape, cap refusal no-partial-state, env override
- `tests/test_skill_command.py` - 1 new test: /skill RuntimeError → prints str(exc), returns True
- `tests/test_skills_load_rpc.py` - 1 new test: load_skill_status RuntimeError → INTERNAL_ERROR with verbatim message

## Decisions Made
- **D-11 wiring in both existing user paths** (per the plan's truth): REPL `/skill` catches RuntimeError after KeyError and prints `str(exc)` returning True; RPC maps RuntimeError → `RPCError(code=INTERNAL_ERROR, message=str(exc))` — the documented `-32603` representation where the verbatim D-11 message IS the contract. KeyError caught first (distinct -32001), ordering safe since KeyError is not a RuntimeError subclass.
- **Cap check before append (H-03):** token accounting + refusal inserted between `body = self._skill_store.load(name)` and the `loaded.append` — a refused load leaves no partial state and never calls `add_skill_message` (D-11 no partial state, no silent drop, no auto-eviction).
- **`e.get("tokens", 0)`** keeps pre-15-03 `name`/`dir`-only records summable — no crash on mixed-shape `skill_state` data (T-15-10).
- **`intersect_allowed_tools()` contract-before-enforcement:** pure function unit-tested in this plan; enforcement wiring deliberately deferred to Phase 17 (ROADMAP criterion 4: Phase 17 implements, never re-decides).
- **`skills/__init__.py` exports both new surfaces** alongside `retain_read_skills` / `manifest_max_chars` — the skills package barrel stays the single import point.

## Deviations from Plan

None - plan executed exactly as written.

## Issues Encountered
- **RED-stage `--co` collection:** As in 15-01, task 1's `--co` acceptance criterion can't literally pass at RED time — `tests/test_skills_filter.py` imports `intersect_allowed_tools`, which doesn't exist yet, so collection reports an ImportError (the same expected RED failure, not a syntax error). After task 3 (GREEN), `--co` collects cleanly and the full run passes. Inherent to the RED scaffold design, not a code defect.

## User Setup Required

None - no external service configuration required.

## Next Phase Readiness
- Phase 16 (TUI integration) consumes the already-shipped `skills.load` RPC + `loadSkill()` TS client (15-01) — the token cap adds no RPC surface changes.
- Phase 17 (allowed-tools enforcement) reads `docs/skills-allowed-tools.md` + `intersect_allowed_tools()` / `retain_read_skills()` — semantics locked, enforcement is implementation-only.
- Threat dispositions T-15-09 (cap refusal, no partial state), T-15-10 (`tokens` never serialized, legacy-tolerant), T-15-11 (cap value in refusal message is a design decision, not a leak), T-15-12 (semantics locked + tested, enforcement transferred to Phase 17) all covered by tests.

---

*Phase: 15-session-behavior-skill-command*
*Completed: 2026-08-02*

## TDD Gate Compliance

| Gate | Commit | Status |
|------|--------|--------|
| RED | `ad42b36` test(15-03): add failing tests for token cap + intersect_allowed_tools | ✓ |
| GREEN | `3c1be7d` feat(15-03): loaded-skill token cap + D-11 REPL/RPC wiring | ✓ |
| GREEN | `c94dd7d` feat(15-03): intersect_allowed_tools CAP-04 contract + Phase 17 decision doc | ✓ |

## Self-Check: PASSED

- FOUND: skills/limits.py
- FOUND: docs/skills-allowed-tools.md
- FOUND: tests/test_skills_filter.py
- FOUND: .planning/phases/15-session-behavior-skill-command/15-03-SUMMARY.md
- FOUND commit: ad42b36 (test, RED gate)
- FOUND commit: 3c1be7d (feat, GREEN gate)
- FOUND commit: c94dd7d (feat, GREEN gate)
