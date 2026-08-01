---
phase: 12-skills-discovery-manifest
plan: 02
subsystem: skills
tags: [discovery, dedupe, win32, allowed-tools, skip-and-warn, frontmatter]

# Dependency graph
requires:
  - phase: 12-skills-discovery-manifest
    provides: SkillInfo frozen dataclass + crash-proof parse_skill_doc splitter (plan 12-01)
provides:
  - One-pass skills discovery (parse_skill_entry per-skill validate + discover_skills deterministic scan)
  - Skip-and-warn taxonomy for every malformed-input class (never raises)
  - Deterministic first-wins dedupe with shadow-warning naming the shadowed skill
  - Frontmatter-name-wins on folder mismatch (D-05), win32 case-insensitive matching (D-06)
  - Shape-only allowed-tools validation (D-15/D-16, enforcement deferred to Phase 17)
affects: [12-03 manifest assembly, 12-04 integration seam, 14-read-skill, 15-session-behavior, 17-allowed-tools-enforcement]

# Tech tracking
tech-stack:
  added: [none — pure stdlib (pathlib, logging, os)]
  patterns: [per-skill try/except skip-and-warn taxonomy, pure _dedupe_key helper for platform-branch testability, sorted() as the single determinism source]

key-files:
  created: [skills/discovery.py, tests/test_skills_discovery.py]
  modified: []

key-decisions:
  - "Frontmatter name is authoritative over folder name — mismatch warns but never skips (D-05); win32 case-only mismatch is silent (D-06)"
  - "Dedupe keys come from a pure _dedupe_key helper (case-insensitive on win32, case-sensitive on posix) so both branches are unit-testable — NTFS cannot physically host case-distinct dirs"
  - "allowed-tools is shape-validated (letters/digits/underscore, non-empty); malformed value is dropped while the skill is kept (D-15/D-16)"
  - "Discovery never raises: OSError/UnicodeDecodeError around the read + parse_skill_doc internal try/except degrade every malformed class to warn+skip (P-07)"

patterns-established:
  - "Skip-and-warn: every malformed skill logs logger.warning naming the dir and returns None — a broken skill never breaks discovery"
  - "Determinism: scan iteration and first-wins both derive from sorted() over case-insensitive folder names"

requirements-completed: [STORE-01, STORE-02, STORE-03, STORE-04, STORE-05]

# Metrics
duration: 2min
completed: 2026-08-01
---

# Phase 12 Plan 2: Skills Discovery Summary

**Skip-and-warn one-pass discovery with deterministic first-wins dedupe: `parse_skill_entry` isolates every malformed-input class behind a per-skill try/except (no SKILL.md, non-UTF8, broken YAML, missing name/description — never raises), and `discover_skills` produces the deduped `list[SkillInfo]` with frontmatter-name-wins (D-05), win32 case-insensitive keys (D-06), and shape-only allowed-tools validation (D-15/D-16) — 16 fixture tests green, full suite at 89**

## Performance

- **Duration:** 2 min
- **Started:** 2026-08-01T18:56:43Z
- **Completed:** 2026-08-01T18:58:38Z
- **Tasks:** 2 (4 commits — TDD RED/GREEN on both tasks)
- **Files modified:** 2

## Accomplishments
- `skills/discovery.py`: `parse_skill_entry(skill_dir) -> SkillInfo | None` with the full skip-and-warn taxonomy — `OSError`/`UnicodeDecodeError` around the UTF-8 read, name/description presence checks, D-05 mismatch warning, D-06 win32 silent case-only match, D-15/D-16 allowed-tools shape validation (malformed → field dropped, skill kept)
- `discover_skills(root) -> list[SkillInfo]`: one-pass deterministic scan over `root/*/SKILL.md` sorted by case-insensitive folder name; first-wins dedupe (D-04) with a warning naming BOTH the winner and the shadowed skill; dedupe keys via pure `_dedupe_key` helper (case-insensitive on win32 per NTFS, case-sensitive on posix); missing/empty root returns `[]` — never raises
- `tests/test_skills_discovery.py`: 16 fixture tests — 9 entry-validation + 7 scan/dedupe, including monkeypatched `os.name="nt"` for the win32 branch and unit-level posix coverage via `_dedupe_key` (NTFS cannot host case-distinct dirs)
- Full suite green at **89 tests** (73 post-12-01 baseline + 16 new), exactly matching the plan's verification target

## Task Commits

Each task was committed atomically:

1. **task 12-02-01 RED: failing tests for parse_skill_entry** - `78edbe9` (test)
2. **task 12-02-01 GREEN: parse_skill_entry with skip-and-warn taxonomy** - `36722e5` (feat)
3. **task 12-02-02 RED: failing tests for discover_skills scan + dedupe** - `73e3864` (test)
4. **task 12-02-02 GREEN: discover_skills with deterministic first-wins dedupe** - `f6a72ce` (feat)

**Plan metadata:** pending final metadata commit (orchestrator-owned per wave contract)

_Note: both tasks were TDD — each test commit (RED) preceded its implementation commit (GREEN). No refactor commits needed; implementations are minimal per the plan's pre-specified code._

## Files Created/Modified
- `skills/discovery.py` - `parse_skill_entry` (per-skill validate + skip-and-warn) + `discover_skills` (deterministic scan + first-wins dedupe) + `_is_valid_tool_name`/`_dedupe_key` helpers; module-level `logger` per CONVENTIONS
- `tests/test_skills_discovery.py` - 16 fixture tests covering all skip classes, dedupe, frontmatter-name-wins, win32/posix case behavior, allowed-tools shapes

## Decisions Made
- Kept `_dedupe_key` as a pure helper (as the plan specified) so the win32/posix case-sensitivity branches are both unit-testable without creating case-distinct directories — NTFS physically cannot host `Foo`/`foo` as separate folders, so the posix branch is tested at unit level and the win32 branch via monkeypatched `os.name` in-scan
- Discovery uses no new dependencies — `pathlib` + `logging` + `os` only, consistent with the "one new runtime dep (PyYAML)" constraint from STACK.md
- Followed the plan's logging convention: every warning names the offending directory or skill so authors know what to fix

## Deviations from Plan

None - plan executed exactly as written. All implementation code matched the plan's pre-specified action blocks verbatim.

## TDD Gate Compliance

| Gate | Commit | Status |
|------|--------|--------|
| RED (task 1) | `78edbe9` test(12-02): add failing tests for parse_skill_entry skip-and-warn | ✓ (failed at collection — module missing) |
| GREEN (task 1) | `36722e5` feat(12-02): implement parse_skill_entry with skip-and-warn taxonomy | ✓ (9 tests pass) |
| RED (task 2) | `73e3864` test(12-02): add failing tests for discover_skills scan + dedupe | ✓ (failed at import — discover_skills missing) |
| GREEN (task 2) | `f6a72ce` feat(12-02): implement discover_skills with deterministic first-wins dedupe | ✓ (16 tests pass) |
| REFACTOR | — | N/A (implementations already minimal and clean) |

Gate sequence validated in git log: each RED commit precedes its GREEN commit.

## Issues Encountered
- None. Both RED phases failed for the correct reason (missing module / missing import — the feature genuinely did not exist), and both GREEN phases passed on first run.

## User Setup Required

None - no external service configuration required.

## Next Phase Readiness
- `discover_skills` produces the deterministic, deduped `list[SkillInfo]` that feeds plan 12-03's budgeted manifest assembly (`build_manifest_text`)
- `parse_skill_entry`'s shape-validated `allowed_tools` fields are ready for Phase 17 enforcement (D-17 — no registry cross-check was performed, as specified)
- Full suite green at 89 tests; knowledge graph refreshed via `graphify update .` after each code task (exits 0)
- Parallel-safe with plan 12-03 (no shared files — discovery.py/manifest.py are separate modules)

## Self-Check: PASSED

- Created files exist: `skills/discovery.py`, `tests/test_skills_discovery.py`, `12-02-SUMMARY.md` — all FOUND on disk
- Commits exist in git log: `78edbe9` (RED 1), `36722e5` (GREEN 1), `73e3864` (RED 2), `f6a72ce` (GREEN 2) — all FOUND
- Plan verification re-run: 16 discovery tests pass; full suite 89 passed; `graphify update .` exits 0 after each code task; grep gates all matched (`def parse_skill_entry`, `def discover_skills`, `def _dedupe_key`, 7 `logger.warning` call sites)

---
*Phase: 12-skills-discovery-manifest*
*Completed: 2026-08-01*
