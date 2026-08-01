---
phase: 12-skills-discovery-manifest
plan: 03
subsystem: skills
tags: [manifest, budget, truncation, sanitize, ellipsis, env-config]

# Dependency graph
requires:
  - phase: 12-skills-discovery-manifest
    provides: SkillInfo frozen dataclass (plan 12-01) + discover_skills deduped list (plan 12-02)
provides:
  - Budgeted manifest assembly (build_manifest_text) with deterministic longest-first truncation — whole skills never dropped (D-10)
  - Character-based cap resolution (manifest_max_chars, D-09) with SKILL_MANIFEST_MAX_CHARS env override, invalid values fall back to 1500
  - Description sanitization for prompt embedding (D-14): newlines/tabs → spaces, control chars removed, single-line contract
  - Empty-entry → None contract (D-13) so the system-prompt seam (plan 12-04) can omit the section entirely
affects: [12-04 integration seam, 14-read-skill, 15-session-behavior]

# Tech tracking
tech-stack:
  added: [none — pure stdlib (logging, os, collections.abc)]
  patterns: [pure assembler function with sequence input, char-budget as a hard invariant (len(result) <= max_chars), longest-first trim with (length, name) deterministic tie-break, per-skill trim warning log]

key-files:
  created: [skills/manifest.py, tests/test_skills_manifest.py]
  modified: []

key-decisions:
  - "Budget measured on the ENTIRE rendered section (heading + bullets) so len(result) <= max_chars is a hard invariant (D-09)"
  - "Truncation marker is the single ellipsis char U+2026; every trimmed description ends with it (D-10)"
  - "Trim selection tie-break: longest description first, then name ascending — deterministic regardless of input order"
  - "Trimmed skills logged via logger.warning naming the skill; whole skills never dropped even if still over-budget after max trim"
  - "manifest_max_chars accepts an injectable env dict (testable) and falls back to 1500 on non-numeric/non-positive values"

patterns-established:
  - "Hard-invariant budget: build_manifest_text guarantees len(result) <= max_chars by construction and is unit-tested"
  - "Determinism: output depends only on the skill set, never on input ordering (sorted() single source)"

requirements-completed: [DISC-02]

# Metrics
duration: 2min
completed: 2026-08-01
---

# Phase 12 Plan 3: Manifest Assembly Summary

**Budgeted manifest assembly: `build_manifest_text` renders the `# Available Skills` section with a hard character cap (default 1,500, env-configurable via `SKILL_MANIFEST_MAX_CHARS`), sanitizes descriptions before embedding (newlines/tabs → spaces, control chars stripped), and when over budget trims the longest descriptions first with a deterministic name-ascending tie-break — every trimmed description ends with the U+2026 ellipsis marker and a warning log names the skill, whole skills are never dropped (D-10), and empty input returns None (D-13) — 9 tests green, full suite at 98**

## Performance

- **Duration:** 2 min
- **Started:** 2026-08-01T13:30:34Z
- **Completed:** 2026-08-01T13:31:59Z
- **Tasks:** 1 (2 commits — TDD RED/GREEN)
- **Files modified:** 2

## Accomplishments
- `skills/manifest.py`: `build_manifest_text(entries, *, max_chars)` assembles the D-11 format (`# Available Skills` heading + `- <name>: <description>` bullets), sanitizes every description via `_sanitize_description` (D-14), enforces the character budget on the **entire rendered section** (D-09, P-01 model-independent chars per research), and trims deterministically longest-first with name-ascending tie-break (D-10) — the trim loop provably terminates (each iteration halves a description ≥ `len(marker)+1`), never drops a whole skill, suffixes every trimmed description with `…` (U+2026), and emits `logger.warning("[skills] manifest cap hit — description trimmed: %s", name)` per trimmed skill
- `manifest_max_chars(env=None)`: resolves the budget from `SKILL_MANIFEST_MAX_CHARS` (injectable env dict for testability); non-numeric or non-positive values fall back to the 1,500 default — a hostile env cannot crash assembly (T-12-08 accepted)
- Empty entry list → `None` (D-13), so the plan 12-04 seam can omit the section entirely with no "(none)" placeholder
- `tests/test_skills_manifest.py`: 9 tests — empty→None, fits-within-budget (no marker), `len(result) <= 500` budget invariant on 30 × 200-char skills, all 30 skills stay listed (D-10), marker + warning naming trimmed skills, deterministic trim (reversed input → identical output), D-14 sanitization (`"line1\nline2\twith  spaced   text\x00\x1b"` → `"line1 line2 with spaced text"`, single line), env-var override + invalid-value fallback, whole-section budget (1 skill × 300 chars under cap 100)
- Full suite green at **98 tests** (89 on-disk baseline incl. 12-02's 16 + 9 new); `graphify update .` exits 0 (knowledge graph: 731 nodes, 1593 edges, 44 communities)

## Task Commits

Each task was committed atomically:

1. **task 12-03-01 RED: failing tests for manifest budget + trim + sanitize** - `74e162a` (test)
2. **task 12-03-01 GREEN: budgeted manifest assembly with longest-first trim** - `866de5c` (feat)

**Plan metadata:** `docs(12-03)` metadata commit follows (executor-owned SUMMARY; STATE.md/ROADMAP.md orchestrator-owned per wave contract)

_Note: single TDD task — test commit (RED) preceded implementation commit (GREEN). No refactor commit needed; implementation is verbatim from the plan's pre-specified action block (minimal by construction)._

## Files Created/Modified
- `skills/manifest.py` - `build_manifest_text` (budgeted assembly + deterministic longest-first trim), `manifest_max_chars` (env override w/ 1500 fallback), `_sanitize_description` (D-14 single-line contract), `_render` helper; module-level `logger` per CONVENTIONS
- `tests/test_skills_manifest.py` - 9 tests covering D-09 budget invariant, D-10 trim determinism/marker/warning, D-13 empty→None, D-14 sanitization, env override

## Decisions Made
- Followed the plan's discretion notes verbatim: marker = single `…` (U+2026) char; budget measured on the entire rendered section (heading + bullets) as a hard invariant; trim tie-break = longest-first then name-ascending (deterministic)
- `manifest_max_chars` takes an optional injected `env` dict (defaults to `os.environ`) — keeps the env-reading logic unit-testable without global monkeypatching of the reading path itself (the test also exercises monkeypatch against the real env)
- No new dependencies — stdlib `logging`/`os`/`collections.abc` only, consistent with the "one new runtime dep (PyYAML)" constraint from STACK.md

## Deviations from Plan

None - plan executed exactly as written. All implementation and test code matched the plan's pre-specified action blocks verbatim.

## TDD Gate Compliance

| Gate | Commit | Status |
|------|--------|--------|
| RED | `74e162a` test(12-03): add failing tests for manifest budget + trim + sanitize | ✓ (failed at collection — ModuleNotFoundError: skills.manifest) |
| GREEN | `866de5c` feat(12-03): implement budgeted manifest assembly with longest-first trim | ✓ (9 tests pass) |
| REFACTOR | — | N/A (implementation already minimal and verbatim from plan) |

Gate sequence validated in git log: RED commit precedes GREEN commit.

## Issues Encountered
- None. RED failed for the correct reason (module genuinely missing — `ModuleNotFoundError: No module named 'skills.manifest'`), GREEN passed on first run.
- **Test-count note (expected, not an issue):** the plan's `<verification>` expected 82 (73 post-12-01 baseline + 9) under the assumption 12-03 runs in parallel with 12-02. In this sequential wave 12-02 had already landed (89 on disk), so the full suite is 98 = 89 + 9. All 9 new tests pass; the authoritative final Phase 12 total (103) is computed in plan 12-04 per the plan's own note.

## User Setup Required

None - no external service configuration required.

## Next Phase Readiness
- `build_manifest_text` is the pure assembler for the plan 12-04 integration seam: it feeds the manifest section into `Session._build_system_prompt()` (D-12 append-at-end contract); the seam calls it with `discover_skills()` output (plan 12-02) and omits the section on `None` (D-13)
- Trim warnings (`[skills] manifest cap hit — description trimmed: <name>`) give authors visibility into which skills are being cut (P-01 warning-sign checklist)
- Full suite green at 98; knowledge graph refreshed via `graphify update .` (exits 0) after the code task

## Self-Check: PASSED

- Created files exist: `skills/manifest.py`, `tests/test_skills_manifest.py` — both FOUND on disk
- Commits exist in git log: `74e162a` (RED), `866de5c` (GREEN) — both FOUND
- Plan verification re-run: 9 manifest tests pass; full suite 98 passed; `graphify update .` exits 0; grep gates all matched (`def build_manifest_text` L46, `def manifest_max_chars` L16, `SKILL_MANIFEST_MAX_CHARS` L13, `TRUNCATION_MARKER` L12, `replace("\n", " ")` L36); TRUNCATION_MARKER verified as U+2026 via `assert TRUNCATION_MARKER == '\u2026'`
- Acceptance criteria (grep gates, 9 tests, graphify, full suite) all PASS — verification loop completed before task close

---
*Phase: 12-skills-discovery-manifest*
*Completed: 2026-08-01*
