---
phase: 14-read-skill-provider-e2e
plan: 02
subsystem: skills
tags: [skills, read_skill, tool-provider, tool-registry, allowed-tools, pytest]

# Dependency graph
requires:
  - phase: 14-read-skill-provider-e2e
    provides: "SkillStore(root) with lookup/load/read_path and traversal guard — the delegate target for the read_skill_path handler"
  - phase: 12-skills-discovery-manifest
    provides: "discovery index + frontmatter-name authority that the injected load/read handlers resolve against"
provides:
  - "Async SkillToolProvider under __skills__ exposing exactly read_skill + read_skill_path, un-namespaced (D-01/D-02)"
  - "retain_read_skills pure retention contract — always keeps the two skill tools under allowed-tools filtering (CAP-03)"
  - "Reserved-name collision guard in ToolRegistry._register_tools — a colliding provider raises ValueError naming the reserved tool (D-03)"
affects: [14-03-load-skill-runtime, 14-04-cancel-mid-gather, 17-allowed-tools, 15-session-behavior]

# Tech tracking
tech-stack:
  added: []
  patterns:
    - "Interface-first provider: SkillToolProvider receives injected async load_handler(name)/read_handler(name, rel) callables — the single shared RuntimeAPI.load_skill path (Pattern 3, D-09); provider never touches Session/context directly"
    - "Reserved-name guard placed BEFORE the generic collision branch in _register_tools — skill names can never shadow or be shadowed (D-03)"

key-files:
  created: [skills/provider.py, skills/filter.py, tests/test_skills_provider.py]
  modified: [tool/registry.py]

key-decisions:
  - "RESERVED_SKILL_TOOLS defined once in skills/provider.py and imported by tool/registry.py — single source of truth for the D-02 reserved names"
  - "Guard added in _register_tools before the generic collision branch; start()'s swallow semantics untouched (Plan 14-03's wiring asserts read_skill is registered and raises visibly)"
  - "No REFACTOR phase — provider/filter implementations are minimal and exactly per the plan's action block"

patterns-established:
  - "Provider contract for __skills__: fetch_tools returns the two reserved schemas, call_tool dispatches to injected handlers, unknown names raise ValueError"
  - "CAP-03 retention contract as a pure function (unit-tested here); enforcement wiring deferred to Phase 17"

requirements-completed: [DISC-03, CAP-03]

# Metrics
duration: 2min
completed: 2026-08-01
---

# Phase 14 Plan 02: SkillToolProvider & Filter Summary

**Async `SkillToolProvider` under `__skills__` exposing exactly the two reserved un-namespaced tools `read_skill` + `read_skill_path` (D-01/D-02) with injected-handler dispatch (Pattern 3, D-09), the `retain_read_skills` pure retention contract that always keeps both skill tools under allowed-tools filtering (CAP-03), and the `ToolRegistry._register_tools` reserved-name guard that rejects any provider shadowing a skill tool (D-03).**

## Performance

- **Duration:** 2 min
- **Started:** 2026-08-01T16:12:51Z
- **Completed:** 2026-08-01T16:14:56Z
- **Tasks:** 2 (TDD: RED + GREEN)
- **Files modified:** 3 created, 1 modified

## Accomplishments

- `skills/provider.py` — async `SkillToolProvider(load_handler=..., read_handler=...)`: `fetch_tools()` returns the two reserved `Tool` schemas (un-namespaced, LLM-facing descriptions + JSON input schemas), `call_tool("read_skill", {"name"})` dispatches to the injected load handler and returns its short ack as the `ToolResult` (D-05 — body never duplicated), `call_tool("read_skill_path", {"skill", "path"})` dispatches to the injected read handler, unknown names raise `ValueError`
- `skills/filter.py` — `retain_read_skills(tools, allowed)` pure function + `RESERVED_SKILL_TOOLS` frozenset: `allowed=None` passes all; otherwise keeps `allowed ∪ {read_skill, read_skill_path}` (CAP-03 deadlock guard, unit-tested here; enforcement wiring is Phase 17)
- `tool/registry.py` — reserved-name guard in `_register_tools` placed before the generic collision branch: registering a reserved skill tool already owned by another provider raises `ValueError` naming the reserved tool and the owner; general collision behavior and `start()` swallow semantics unchanged
- `tests/test_skills_provider.py` — 11-test suite: provider surface (2 tools, un-namespaced, schemas), read_skill dispatch + D-05 ack-not-body, read_skill_path dispatch, unknown-name rejection, CAP-03 retention (empty/union/None), shared reserved-constant contract, and the D-03 registry collision test via a stub provider holding `read_skill`
- Knowledge graph refreshed via `graphify update .` per AGENTS.md

## TDD Execution

- **RED:** `tests/test_skills_provider.py` (188 lines, 11 tests). Failed at collection with `ModuleNotFoundError: No module named 'skills.filter'` — the correct RED reason (both `skills.provider` and `skills.filter` absent).
- **GREEN:** `skills/provider.py` (57 lines) + `skills/filter.py` (12 lines) + `tool/registry.py` guard (6 lines). Provider tests: 11 passed. Full suite: 138 passed, 1 skipped (baseline 127 + 1 skipped → +11).
- **REFACTOR:** None — implementations are minimal and exactly per the plan's action block.

## task Commits

Each task was committed atomically:

1. **task 1: RED — tests for SkillToolProvider surface + filter retention** - `569e2cd` (test)
2. **task 2: GREEN — implement SkillToolProvider, filter, and registry reservation** - `4006219` (feat)

**Plan metadata:** `pending` (docs commit after SUMMARY)

## Files Created/Modified

- `skills/provider.py` - Async `SkillToolProvider`: the two reserved tool schemas + injected-handler dispatch (contracts Plan 14-03's `RuntimeAPI.load_skill()` implements); `RESERVED_SKILL_TOOLS` single source of truth
- `skills/filter.py` - `retain_read_skills` pure retention function + `RESERVED_SKILL_TOOLS` (CAP-03 contract, unit-tested)
- `tool/registry.py` - `_register_tools` reserved-name guard (D-03): colliding provider raises ValueError naming the reserved tool
- `tests/test_skills_provider.py` - 11-test provider-surface/filter/collision suite (async, `asyncio_mode = auto`)

## Decisions Made

- **Single source of truth:** `RESERVED_SKILL_TOOLS` defined in `skills/provider.py`, imported by `tool/registry.py` — no duplicated constant to drift. (`skills/filter.py` re-defines its own copy per the plan's action block; a test asserts both match.)
- **Guard placement:** reserved-name check added before the generic collision branch in `_register_tools`, matching the plan exactly. `start()`'s swallow-and-log semantics intentionally untouched — Plan 14-03's wiring will assert `read_skill` is registered and raise visibly (T-14-01 second leg).
- **No REFACTOR phase:** provider/filter are minimal per plan; no cleanup opportunities worth a separate commit.

## Deviations from Plan

None - plan executed exactly as written.

## Issues Encountered

None.

## User Setup Required

None - no external service configuration required.

## Next Phase Readiness

- The `__skills__` provider contracts are locked: Plan 14-03 implements `RuntimeAPI.load_skill()` and injects `load_handler`/`read_handler` — SkillStore is the delegate target for both (path-safety boundary already shipped in 14-01).
- The D-03 registry guard is in place; Plan 14-03's wiring registers `add_provider("__skills__", provider, namespace=None)` and asserts `read_skill` present after `start()`.
- `retain_read_skills` is the CAP-03 contract for Phase 17's allowed-tools enforcement; enforcement wiring lands there.
- Full suite at 138 passed + 1 skipped, ready for the next plan in the wave.

## Self-Check: PASSED

- `skills/provider.py` exists: True
- `skills/filter.py` exists: True
- `tool/registry.py` contains reserved-name guard: True
- `tests/test_skills_provider.py` exists: True
- Commit `569e2cd` (test 14-02 RED) present in git log
- Commit `4006219` (feat 14-02 GREEN) present in git log
- `python -m pytest tests/test_skills_provider.py -x` → 11 passed
- `python -m pytest -q` → 138 passed, 1 skipped
- `registry.list_tools()` with `__skills__` registered → exactly `['read_skill', 'read_skill_path']`, un-namespaced

---

*Phase: 14-read-skill-provider-e2e*
*Completed: 2026-08-01*
