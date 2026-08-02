---
phase: 14-read-skill-provider-e2e
plan: 05
subsystem: skills
tags: [skills, load_skill, dedup, case-insensitive, win32, H-01, gap-closure, tdd, pytest]

# Dependency graph
requires:
  - phase: 14-read-skill-provider-e2e
    plan: 03
    provides: "RuntimeAPI.load_skill single shared load path with skill_state['loaded'] dedup — the method this plan's fix targets"
  - phase: 14-read-skill-provider-e2e
    plan: 01
    provides: "SkillStore.lookup() with case-insensitive _key() on win32 — the lookup contract the dedup now aligns with"
  - phase: 12-skills-discovery-manifest
    provides: "Frontmatter-name authority (D-04/D-05) — info.name is the canonical name the dedup compares against"

provides:
  - "H-01 gap closed: load_skill dedup compares the CANONICAL info.name from SkillStore.lookup() (case-insensitive on win32) instead of the raw caller name — case-variant re-loads ('demo-greeter' → 'DEMO-GREETER') are no-op 'already loaded' acks, body injected exactly once (D-07, ACT-02, ROADMAP SC1)"
  - "H-03 latent TOCTOU hardening: loaded.append happens BEFORE the add_skill_message await (mark-before-inject), zero extra lines"
  - "Two regression tests (unit in tests/test_load_skill.py + E2E in tests/test_skills_e2e.py) pinning exactly-once for case-variant re-loads; both RED pre-fix, GREEN post-fix"
affects: [15-session-behavior, 16-tui-integration, 17-allowed-tools]

# Tech tracking
tech-stack:
  added: []
  patterns:
    - "Dedup key == lookup key: load_skill dedups against the canonical name returned by the case-insensitive lookup — the loaded-record name and the dedup key are the same string (fixes the H-01 key disagreement)"
    - "Mark-before-inject ordering: record appended before the injection await closes TOCTOU windows against future suspension points"

key-files:
  created: []
  modified: [harness/runtime.py, tests/test_load_skill.py, tests/test_skills_e2e.py]

key-decisions:
  - "Dedup compares e['name'] == info.name (canonical post-lookup name) rather than the raw caller name — consistent with SkillStore._key() case-insensitive normalization on win32"
  - "lookup() moved BEFORE the dedup check — unknown names still raise KeyError naming the raw name (unchanged observable behavior); unknown names can never be in loaded"
  - "Mark-before-inject: loaded.append before the await session.context.add_skill_message(...) — H-03 TOCTOU hardening folded into the H-01 fix at zero extra cost"
  - "No-op ack returns the canonical name ('Skill 'demo-greeter' already loaded') — existing tests assert only 'already loaded' in ack.lower(), unaffected"

requirements-completed: [ACT-02, DISC-03]

# Metrics
duration: 12min
completed: 2026-08-02
---

# Phase 14 Plan 05: Case-Variant Dedup (H-01 Gap Closure) Summary

**H-01 fixed: `RuntimeAPI.load_skill` dedup now compares the canonical `info.name` from `SkillStore.lookup()` (case-insensitive on win32) instead of the raw caller name — `load_skill('demo-greeter')` then `load_skill('DEMO-GREETER')` is a no-op "already loaded" ack with exactly one system body and one `skill_state['loaded']` record, restoring D-07/ACT-02/ROADMAP SC1 exactly-once on the primary platform.**

## Performance

- **Duration:** 12 min
- **Started:** 2026-08-02T18:22:00Z (approx)
- **Completed:** 2026-08-02T18:34:07Z
- **Tasks:** 2 (TDD: RED test commit + GREEN fix commit)
- **Files modified:** 3 (2 test files, 1 production file)

## Accomplishments

- **H-01 gap closed:** `harness/runtime.py` `load_skill` dedup key changed from the raw caller name (`e["name"] == name`, case-sensitive) to the canonical post-lookup name (`e["name"] == info.name`) — consistent with `SkillStore._key()` case-insensitive normalization on win32 (`os.name == 'nt'`). The exact VERIFICATION.md repro (`demo-greeter` → `DEMO-GREETER`) now returns `Skill 'demo-greeter' already loaded`, exactly 1 body, exactly 1 record.
- **Mark-before-inject (H-03 hardening):** `loaded.append({"name": info.name, "dir": str(info.path)})` moved BEFORE `await session.context.add_skill_message(...)` — closes the latent check-then-await-then-append TOCTOU at zero extra lines; no observable behavior change today (no suspension point in `add_skill_message`), future-proofs against any await added there.
- **Two regression tests shipped:** unit test in `tests/test_load_skill.py` (real RuntimeAPI + real SkillStore) and E2E test in `tests/test_skills_e2e.py` (real SkillStore + ToolRegistry + SkillToolProvider). Both fail RED on pre-fix win32 code with the H-01 symptom (`Loaded skill demo-greeter` returned on the second load) and pass GREEN post-fix. The `try/except KeyError` guard keeps the tests valid on posix (case-sensitive lookup) while always asserting exactly-once.
- **Unknown-name behavior unchanged:** `load_skill('no-such-skill')` still raises `KeyError: "Unknown skill 'no-such-skill'"` — spot-checked.

## TDD Execution

- **RED:** Added `test_case_variant_reload_never_double_injects` to both test files (no production changes). Run: 2 failed, 13 passed. The failure was the exact H-01 symptom — on win32 the second `load_skill("DEMO-GREETER")` returned `Loaded skill demo-greeter` (bypassing dedup) instead of an "already loaded" ack.
- **GREEN:** Replaced the dedup + injection block in `harness/runtime.py` per the plan's action block (canonical-name dedup, lookup-before-dedup, mark-before-inject, canonical no-op ack) + docstring note. Run: 15 passed (2 new tests GREEN), then full suite 156 passed, 1 skipped, 0 failures.
- **REFACTOR:** None — implementation is minimal and exactly per the plan's action block.

## task Commits

Each task was committed atomically:

1. **task 1 (RED): failing case-variant dedup regression** - `c4bfb44` (test)
2. **task 2 (GREEN): dedup load_skill against canonical skill name** - `d5ed6a2` (fix)

**Plan metadata:** `pending` (docs commit after SUMMARY)

## Files Created/Modified

- `harness/runtime.py` - `load_skill`: dedup check now `e["name"] == info.name` (canonical, post-lookup); `lookup()` moved before dedup; `loaded.append` before the injection await (mark-before-inject); no-op ack uses canonical name; docstring H-01 note
- `tests/test_load_skill.py` - Added `test_case_variant_reload_never_double_injects` (unit: real RuntimeAPI + real SkillStore, exactly-one body + one record)
- `tests/test_skills_e2e.py` - Added `test_case_variant_reload_never_double_injects` (E2E: real SkillStore + ToolRegistry + SkillToolProvider stack)

## Decisions Made

- **Canonical-name dedup (VERIFICATION.md missing item #1):** dedup compares against `info.name` returned by the case-insensitive `SkillStore.lookup()` — the loaded record and the dedup key are the same canonical string, eliminating the H-01 key disagreement. Chosen over case-normalizing the loaded records because `info.name` is already the single source of truth (frontmatter-name authority, D-04).
- **lookup before dedup:** unknown names still raise `KeyError` naming the raw name (unchanged observable behavior); a lookup failure can never be masked by dedup.
- **Mark-before-inject (VERIFICATION.md H-03 hardening, deferred_scope_notes):** record appended before the injection await — folded into the H-01 fix lines at zero extra cost, per the plan.
- **No-op ack canonical name:** `Skill 'demo-greeter' already loaded` — matches the D-07 ack contract; existing tests assert only `"already loaded" in ack.lower()`, unaffected.

## Deviations from Plan

None - plan executed exactly as written. Both `must_haves` truths, all `artifacts`, and both `key_links` verified.

## Issues Encountered

- **Transient:** inline PowerShell `python -c` spot-check failed twice on quote escaping (`unterminated string literal`) and module path (`ModuleNotFoundError: No module named 'harness'` — script run from temp dir, project not on `sys.path`). Resolved by writing a temp script and running with `PYTHONPATH=C:\personal\AgentHarness`. No code impact — the spot-check then passed cleanly.

## TDD Gate Compliance

- RED gate: `c4bfb44` `test(14-05): add failing case-variant dedup regression (H-01)` — present, and the test genuinely failed pre-fix for the right reason (H-01 symptom, not import/syntax error).
- GREEN gate: `d5ed6a2` `fix(14-05): dedup load_skill against canonical skill name (H-01)` — present, tests pass after implementation.
- REFACTOR gate: N/A (no refactor needed — minimal implementation). No violations.

## Known Stubs

None — no stubs introduced. The two new tests assert real behavior against real stacks; production change is a 10-line swap in an existing method.

## Threat Flags

None — no new attack surface. The changed lines touch only the dedup comparison and record ordering inside the existing `load_skill` method; `SkillStore` (T-14-02 traversal guard) and the reserved-name collision guard (T-14-01) are untouched. T-14-07 (case-variant dedup bypass) and T-14-08 (TOCTOU) are mitigated per the plan's threat register; T-14-09/T-14-10 remain accepted-deferred per the plan's threat_model.

## User Setup Required

None - no external service configuration required.

## Next Phase Readiness

- **Phase 14 gap closed:** the phase's 1 failed truth (D-07/ACT-02 exactly-once for case variants) is now verified — full suite at 156 passed, 1 skipped.
- The exactly-once contract holds for identical strings AND case variants on win32; `/skill` (Phase 15), the TUI indicator (Phase 16), and allowed-tools filtering (Phase 17) all read `skill_state["loaded"]`, which now never accumulates duplicate records.
- Deferred hardening items from 14-VERIFICATION.md remain open (H-02 RPC stdout `print()` banners, M-01 index-based cancel rollback, M-02 read_skill_path loaded-check) — per the plan's deferred_scope_notes, none are picked up by Phases 15/16/17.

## Self-Check: PASSED

- `harness/runtime.py` contains `e["name"] == info.name` (exactly 1 match in `load_skill`): True
- `loaded.append({"name": info.name, "dir": str(info.path)})` (line 199) appears BEFORE `await session.context.add_skill_message(...)` (line 201): True
- `test_case_variant_reload_never_double_injects` present in BOTH `tests/test_load_skill.py` (line 176) and `tests/test_skills_e2e.py` (line 200): True
- `python -m pytest tests/test_load_skill.py tests/test_skills_e2e.py -q` → 15 passed: True
- `python -m pytest -q` → 156 passed, 1 skipped, 0 failures: True
- Commit `c4bfb44` (RED) and `d5ed6a2` (GREEN) present in git log: True
- Spot-check: `load_skill('demo-greeter')` → `Loaded skill demo-greeter`; `load_skill('DEMO-GREETER')` → `Skill 'demo-greeter' already loaded`; body-count 1; record-count 1; `load_skill('no-such-skill')` → `KeyError: "Unknown skill 'no-such-skill'"`: True

---

*Phase: 14-read-skill-provider-e2e*
*Completed: 2026-08-02*
