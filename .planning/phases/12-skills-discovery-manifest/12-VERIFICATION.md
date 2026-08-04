---
phase: 12-skills-discovery-manifest
verified: 2026-08-01T19:18:04Z
status: passed
score: 10/10 must-haves verified
overrides_applied: 0
deferred:
  - truth: "Manifest construction sites wired to the production `.agentharness/skills/` directory (main.py / harness/runtime.py) so a real REPL session shows the section"
    addressed_in: "Phase 14"
    evidence: "Plan 12-04 summary: 'Phase 14 (read_skill provider) can wire the production construction sites (main.py/harness/runtime.py): build the manifest from discover_skills() + build_manifest_text() and set session.skill_manifest before agent runs — the seam is proven with the same public functions'. VALIDATION.md: 'Deferred to Phase 14 E2E: author a skill under .agentharness/skills/, start the REPL, inspect the first system block'."
  - truth: "allowed-tools cross-checked against the tool registry"
    addressed_in: "Phase 17"
    evidence: "Plan 12-02 D-17: 'shape-only — never cross-check tool names against the registry (Phase 17 concern)'. ROADMAP Phase 17: 'allowed-tools Enforcement & Hardening — tool-list filtering, intersection semantics'."
---

# Phase 12: Skills Discovery & Manifest Verification Report

**Phase Goal:** SKILL.md authoring, discovery with skip-and-warn, budgeted manifest in the system prompt
**Verified:** 2026-08-01T19:18:04Z
**Status:** passed
**Re-verification:** No — initial verification

## Goal Achievement

### Observable Truths

| #   | Truth   | Status     | Evidence       |
| --- | ------- | ---------- | -------------- |
| 1   | User can author a skill as `.agentharness/skills/<name>/SKILL.md` (one folder per skill) with required `name`+`description` and optional `allowed-tools` frontmatter (ROADMAP SC1) | ✓ VERIFIED | `discover_skills(root)` scans `root/*/SKILL.md` (one folder per skill, `skills/discovery.py:104`); `parse_skill_entry` enforces required name/description and optional allowed-tools (`discovery.py:52-88`); live E2E wrote real SKILL.md dirs and discovered them. Production root constant wiring deferred to Phase 14 (see Deferred Items) |
| 2   | Agent sees a manifest listing every valid skill's `name` + `description` in the system prompt each turn — no skill body loaded by the manifest alone (ROADMAP SC2) | ✓ VERIFIED | `Session.skill_manifest` field (`session/models.py:46`); `_build_system_prompt()` appends it every `to_llm_messages()` call (`models.py:71-72`); `test_manifest_stable_across_calls` proves per-call rebuild (D-08); live E2E confirmed section present in system block |
| 3   | The manifest never exceeds its character budget (~1,500 chars): over-long descriptions trimmed deterministically, trimmed skills logged with a warning (ROADMAP SC3) | ✓ VERIFIED | `build_manifest_text` enforces `len(result) <= max_chars` on the whole section (`skills/manifest.py:46-82`); longest-first trim with `…` marker + `logger.warning`; live E2E: 30×200-char skills under 500-char cap, all names kept, marker present; env override via `SKILL_MANIFEST_MAX_CHARS` |
| 4   | A skill with missing/invalid frontmatter is skipped with a warning and never breaks the harness; duplicate names resolve first-wins deterministically with a warning naming the shadowed skill (ROADMAP SC4) | ✓ VERIFIED | Full skip-and-warn taxonomy (`discovery.py:41-88` — no SKILL.md, non-UTF8, broken YAML, missing name/description); first-wins dedupe over sorted scan naming BOTH winner and shadowed skill (`discovery.py:102-119`); live E2E on win32: malformed skipped, dup resolved to first body, warnings emitted |
| 5   | A malformed SKILL.md (broken YAML, no delimiters, non-dict YAML, CRLF, empty) degrades to `({}, body)` — parse never raises | ✓ VERIFIED | `parse_skill_doc` (`skills/frontmatter.py:6-31`) with `yaml.safe_load` + `isinstance(meta, dict)` guard; 7 fixture tests pass incl. CRLF body-strip |
| 6   | The frontmatter `name` is authoritative over the folder name (mismatch warns, never skips; win32 case-only mismatch silent) | ✓ VERIFIED | `discovery.py:63-74` (D-05/D-06); `test_frontmatter_name_wins_over_folder_name` + `test_case_only_mismatch_silent_on_win32` pass; live win32 run confirmed case-insensitive dedupe (NTFS) |
| 7   | allowed-tools is shape-validated: valid list kept; malformed value dropped with a warning while the skill is kept | ✓ VERIFIED | `discovery.py:76-87` (D-15/D-16); `test_allowed_tools_valid_list_kept`, `test_allowed_tools_malformed_dropped_skill_kept`, `test_allowed_tools_bad_shape_dropped` pass |
| 8   | No valid skills → `build_manifest_text` returns None (the system-prompt seam omits the section entirely) | ✓ VERIFIED | `manifest.py:59-60` (D-13); `test_empty_entries_returns_none` + `test_no_valid_skills_omits_section` pass; live E2E confirmed None → no `# Available Skills` |
| 9   | Newlines and control characters are stripped from descriptions before embedding | ✓ VERIFIED | `_sanitize_description` (`manifest.py:29-38`, D-14); `test_description_sanitized_for_embedding` passes (`"line1\nline2\twith  spaced   text\x00\x1b"` → single-line sanitized) |
| 10  | The manifest is a non-serialized Session field — `to_snapshot_meta()` never contains it, JSONL session file stays untouched | ✓ VERIFIED | `to_snapshot_meta()` copies explicit fields only (`session/models.py:108-117`); `test_manifest_never_serialized_to_snapshot` passes; live E2E confirmed no `skill_manifest` key in snapshot |

**Score:** 10/10 truths verified

### Deferred Items

Items not yet met but explicitly addressed in later milestone phases (informational — do not block this phase).

| # | Item | Addressed In | Evidence |
|---|------|-------------|----------|
| 1 | Production wiring: build manifest from the real `.agentharness/skills/` dir and set `session.skill_manifest` at agent-run construction sites (`main.py`/`harness/runtime.py`); REPL E2E inspection | Phase 14 | Plan 12-04 summary + VALIDATION.md line 69 explicitly defer to Phase 14 E2E |
| 2 | allowed-tools enforcement (registry cross-check, tool-list filtering) | Phase 17 | D-17 locked decision; ROADMAP Phase 17 covers filtering/hardening |

### Required Artifacts

| Artifact | Expected    | Status | Details |
| -------- | ----------- | ------ | ------- |
| `requirements.txt` | PyYAML single new dep | ✓ VERIFIED | Line 6: `PyYAML>=6.0.3`, no trailing blank line; import verified (tests import yaml) |
| `skills/models.py` | `SkillInfo` frozen dataclass | ✓ VERIFIED | `@dataclass(frozen=True)`, name/description/path/`allowed_tools=()`; import smoke passed |
| `skills/frontmatter.py` | `parse_skill_doc` splitter | ✓ VERIFIED | 31 lines, `yaml.safe_load` only, `lstrip("\r\n")`, all 7 tests green |
| `skills/discovery.py` | `parse_skill_entry` + `discover_skills` | ✓ VERIFIED | 119 lines, full skip-and-warn taxonomy, deterministic dedupe, 16 tests green |
| `skills/manifest.py` | `build_manifest_text` + `manifest_max_chars` | ✓ VERIFIED | 82 lines, budget invariant, deterministic trim, sanitize, 9 tests green |
| `skills/__init__.py` | Complete barrel (5 public names) | ✓ VERIFIED | `__all__` = SkillInfo, parse_skill_doc, discover_skills, build_manifest_text, manifest_max_chars; import smoke passed |
| `session/models.py` | `skill_manifest` field + `_build_system_prompt` append | ✓ VERIFIED | Field L46, append L71-72 (truthiness-gated), `to_snapshot_meta` untouched |
| `tests/test_skills_frontmatter.py` | 7 fixture tests | ✓ VERIFIED | All pass |
| `tests/test_skills_discovery.py` | 16 fixture tests | ✓ VERIFIED | All pass |
| `tests/test_skills_manifest.py` | 9 budget/trim/sanitize tests | ✓ VERIFIED | All pass |
| `tests/test_skills_integration.py` | 5 end-to-end seam tests | ✓ VERIFIED | All pass |

### Key Link Verification

| From | To  | Via | Status | Details |
| ---- | --- | --- | ------ | ------- |
| `skills/frontmatter.py` | `yaml` | `yaml.safe_load` (L24) | ✓ WIRED | SafeLoader only; never `yaml.load` (T-12-01) |
| `skills/__init__.py` | `skills/models.py` | barrel re-export `SkillInfo` (L4) | ✓ WIRED | Import smoke passed |
| `skills/discovery.py` | `skills/frontmatter.py` | `parse_skill_doc` import (L7) | ✓ WIRED | Used at L50 |
| `skills/discovery.py` | `skills/models.py` | `SkillInfo` construction (L8, L88) | ✓ WIRED | Live E2E confirmed |
| `skills/discovery.py` | `logging` | `logger.warning` (7 call sites) | ✓ WIRED | Warnings name file/skill — verified in live run output |
| `skills/manifest.py` | `skills/models.py` | `SkillInfo` input (L7, L41) | ✓ WIRED | |
| `skills/manifest.py` | `os.environ` | `SKILL_MANIFEST_MAX_CHARS` (L13, L21) | ✓ WIRED | Env override + fallback tested |
| `skills/manifest.py` | `logging` | `logger.warning` per trimmed skill (L81) | ✓ WIRED | Live E2E showed all 30 trimmed skills warned |
| `session/models.py` | `self.skill_manifest` | `if self.skill_manifest: parts.append(...)` (L71-72) | ✓ WIRED | D-12 append-last verified by test + live index check |
| `session/models.py` | `# Available Skills` (manifest string) | `to_llm_messages()` → `_build_system_prompt()` renders prebuilt string | ✓ WIRED | Live E2E: section present, index after `# Environment` |
| `skills/__init__.py` | `skills/discovery.py` | barrel export `discover_skills` (L1) | ✓ WIRED | |

### Data-Flow Trace (Level 4)

| Artifact | Data Variable | Source | Produces Real Data | Status |
| -------- | ------------- | ------ | ------------------ | ------ |
| `skills/manifest.py` | `descs` / `text` | `SkillInfo` descriptions from `discover_skills` (real SKILL.md reads) | ✓ Yes — live E2E wrote real files, read via `read_text(utf-8)`, parsed, rendered | ✓ FLOWING |
| `session/models.py` | `self.skill_manifest` | `build_manifest_text(discover_skills(root))` — populated by caller (Phase 14 production wiring; tests populate it) | ✓ Yes — set from real discovered data in tests + live E2E; no hardcoded/empty default in the render path | ✓ FLOWING |

### Behavioral Spot-Checks

| Behavior | Command | Result | Status |
| -------- | ------- | ------ | ------ |
| Barrel exports all 5 public names | `python -c "from skills import ..."` | `barrel ok: True` | ✓ PASS |
| Skip-and-warn discovery (2 valid + 1 broken) | live E2E script | Broken skipped with warning naming dir; `['code-review', 'graphify']` discovered | ✓ PASS |
| Manifest ≤ budget, all names kept | live E2E: 30×200-char under 500 | `len(out) <= 500`, all 30 `- s{i}:` present, `…` marker present | ✓ PASS |
| Section appended after Environment (D-12) | live E2E index check | `# Available Skills` index > `# Environment` index | ✓ PASS |
| Non-serialization guard | live E2E snapshot check | `'skill_manifest' not in to_snapshot_meta()` | ✓ PASS |
| Empty input → None → section omitted | live E2E | `build_manifest_text([])` is None; no `# Available Skills` in system block | ✓ PASS |
| First-wins dedupe + shadow warning (win32) | live E2E: a-dup/b-dup folders | One `dup` entry with first body; warning names `b-dup`; malformed skipped | ✓ PASS |
| Full Phase 12 test suite | `python -m pytest tests/test_skills_*.py -q` | 37 passed (7+16+9+5) | ✓ PASS |
| Full project suite (no regressions) | `python -m pytest -q` | 103 passed — exactly the plan's target (66+37) | ✓ PASS |
| Claimed commits exist | `git log` | All 12 commits (3eb8275 … 6926e6b) found, RED precedes GREEN | ✓ PASS |

### Requirements Coverage

| Requirement | Source Plan | Description | Status | Evidence |
| ----------- | ---------- | ----------- | ------ | -------- |
| STORE-01 | 12-01, 12-02 | Author skill as `SKILL.md` at `.agentharness/skills/<name>/SKILL.md` | ✓ SATISFIED | `discover_skills` scans `root/*/SKILL.md` — folder-per-skill structure fully supported and test-proven; production root constant wired in Phase 14 (deferred, documented) |
| STORE-02 | 12-02 | Skill name is kebab-case and matches the folder name | ✓ SATISFIED | Folder-match enforced with warning, frontmatter-name-wins (D-05); kebab-case deliberately lenient per locked decision D-07 (12-CONTEXT.md L25: "Kebab-case is a documented convention, not an enforcement rule") |
| STORE-03 | 12-01, 12-02 | `name` + `description` required, `allowed-tools` optional | ✓ SATISFIED | `parse_skill_entry` validates name/description presence (skip if missing), allowed-tools optional w/ shape validation |
| STORE-04 | 12-02 | Missing/invalid frontmatter skipped with warning, never breaks harness | ✓ SATISFIED | Full skip-and-warn taxonomy; `test_discovery_skips_malformed_never_raises`; live E2E confirmed |
| STORE-05 | 12-02 | Duplicate names resolve first-wins deterministically with warning about shadowed skill | ✓ SATISFIED | Sorted-scan first-wins; warning names both winner + shadowed; `test_duplicate_names_first_wins`; live E2E confirmed |
| DISC-01 | 12-04 | Agent sees manifest of every skill's name+description in system prompt each turn | ✓ SATISFIED | `Session.skill_manifest` + `_build_system_prompt` append per `to_llm_messages()` call (D-08); integration tests + live E2E; production call-site wiring Phase 14 (deferred) |
| DISC-02 | 12-03, 12-04 | Manifest subject to budget with trimming of over-long skills | ✓ SATISFIED | `build_manifest_text` hard char cap (1500 default / env), deterministic longest-first trim, marker + warnings; tests + live E2E |

All 7 requirement IDs from the phase requirement set appear in at least one PLAN's frontmatter (12-01: STORE-01/03; 12-02: STORE-01..05; 12-03: DISC-02; 12-04: DISC-01/02). Union = STORE-01..05 + DISC-01..02 — zero orphaned requirements, zero unclaimed IDs.

### Anti-Patterns Found

| File | Line | Pattern | Severity | Impact |
| ---- | ---- | ------- | -------- | ------ |
| `skills/frontmatter.py` | 14, 22 | `return {}, text` | ℹ️ Info | LEGITIMATE — the documented crash-proof degradation fallback (D-03), not a stub; every path is either the fallback or a parsed result |
| `skills/discovery.py` | 101 | `return []` | ℹ️ Info | LEGITIMATE — empty-root contract (`discover_skills` on missing/empty dir returns `[]`, never raises) |
| `skills/manifest.py` | 52 | `"(none)" placeholder` (docstring) | ℹ️ Info | LEGITIMATE — docstring describing the D-13 contract (no placeholder is emitted); not executable code |

No TODO/FIXME/HACK/XXX comments, no placeholder components, no hardcoded-empty data feeding renders, no console.log-only implementations found in any Phase 12 file.

### Human Verification Required

None. The phase's own VALIDATION.md defines the "manifest visible in a real running REPL" check as **Phase 14 E2E scope** (production wiring does not exist in Phase 12 by design — `main.py`/`harness/runtime.py` construction sites are Phase 14). Every in-scope behavior for this phase was verified programmatically: 37 Phase 12 unit/integration tests, a live end-to-end script exercising the actual public API (discover → build → set → `to_llm_messages()`), and the full 103-test regression suite.

### Gaps Summary

No gaps found. All 10 must-have truths verified, all 11 required artifacts exist and are substantive and wired, all 11 key links connected, Level 4 data-flow confirmed real (no hollow/static sources), all 7 requirements satisfied, 103/103 tests green, no stubs or blocker anti-patterns.

Two items are intentionally not delivered in this phase and are documented deferrals to later phases (see Deferred Items): (1) production wiring of the `.agentharness/skills/` manifest construction sites — Phase 14; (2) allowed-tools registry enforcement — Phase 17 (D-17 locked decision).

---

_Verified: 2026-08-01T19:18:04Z_
_Verifier: OpenCode (gsd-verifier)_
