---
phase: 12
slug: skills-discovery-manifest
status: draft
nyquist_compliant: true
wave_0_complete: false
created: 2026-08-01
---

# Phase 12 — Validation Strategy

> Per-phase validation contract for feedback sampling during execution.

---

## Test Infrastructure

| Property | Value |
|----------|-------|
| **Framework** | pytest 7.x (existing — verified 66 tests green pre-phase) |
| **Config file** | `pytest.ini` (`asyncio_mode = auto`, `testpaths = tests`) |
| **Quick run command** | `python -m pytest tests/test_skills_frontmatter.py tests/test_skills_discovery.py tests/test_skills_manifest.py tests/test_skills_integration.py -q` |
| **Full suite command** | `python -m pytest -q` |
| **Estimated runtime** | ~10 seconds |

---

## Sampling Rate

- **After every task commit:** Run the quick command (targeted skills tests)
- **After every plan wave:** Run `python -m pytest -q` (full suite)
- **Before `/gsd-verify-work`:** Full suite must be green
- **Max feedback latency:** ~10 seconds

---

## Per-task Verification Map

| task ID | Plan | Wave | Requirement | Threat Ref | Secure Behavior | Test Type | Automated Command | File Exists | Status |
|---------|------|------|-------------|------------|-----------------|-----------|-------------------|-------------|--------|
| 12-01-01 | 01 | 1 | STORE-01, STORE-03 | T-12-01 | `SkillInfo` dataclass + `__all__` barrel; PyYAML added to requirements.txt | unit | `python -m pytest tests/ -q` (import smoke) | ❌ W0 | ⬜ pending |
| 12-01-02 | 01 | 1 | STORE-03 | T-12-01 | `parse_skill_doc` degrades to `({}, text)` on any malformed input; CRLF handled | unit | `python -m pytest tests/test_skills_frontmatter.py -q` | ❌ W0 | ⬜ pending |
| 12-02-01 | 02 | 2 | STORE-02, STORE-04, STORE-03 | T-12-01, T-12-04 | Per-skill try/except: broken YAML / missing name / empty / non-UTF8 / no SKILL.md → warn + skip, never raise; allowed-tools shape (D-15/16) | unit | `python -m pytest tests/test_skills_discovery.py -q` | ❌ W0 | ⬜ pending |
| 12-02-02 | 02 | 2 | STORE-01, STORE-05 | T-12-06 | Deterministic scan; first-wins dedupe with shadow warning; frontmatter-name-wins (D-05); win32 case-match (D-06) | unit | `python -m pytest tests/test_skills_discovery.py -q` | ❌ W0 | ⬜ pending |
| 12-03-01 | 03 | 2 | DISC-02 | T-12-05, T-12-03 | Budget cap in chars (D-09); longest-first trim, all skills listed, ellipsis + warning (D-10); sanitize (D-14); None when empty (D-13); env override | unit | `python -m pytest tests/test_skills_manifest.py -q` | ❌ W0 | ⬜ pending |
| 12-04-01 | 04 | 3 | DISC-01, DISC-02 | T-12-03 | `skill_manifest` field (non-serialized); `_build_system_prompt` appends `# Available Skills` after CWD (D-11/12); omitted when None (D-13) | unit | `python -m pytest tests/test_skills_integration.py -q` | ❌ W0 | ⬜ pending |
| 12-04-02 | 04 | 3 | DISC-01, DISC-02 | T-12-03 | End-to-end: temp skills dir → discover → build_manifest_text → set on Session → `to_llm_messages()` system block contains entries; empty dir → no section | unit | `python -m pytest tests/test_skills_integration.py -q` | ❌ W0 | ⬜ pending |

*Status: ⬜ pending · ✅ green · ❌ red · ⚠️ flaky*

---

## Wave 0 Requirements

- [ ] `tests/test_skills_frontmatter.py` — stubs for STORE-03 (frontmatter parsing)
- [ ] `tests/test_skills_discovery.py` — stubs for STORE-01..05 (entry validation + scan/dedupe)
- [ ] `tests/test_skills_manifest.py` — stubs for DISC-02 (budget/trim/sanitize)
- [ ] `tests/test_skills_integration.py` — stubs for DISC-01, DISC-02 (system-prompt seam)
- [ ] `python -m pip install "PyYAML>=6.0.3"` — required before any skills test can import `yaml` (env verified missing 2026-08-01)

*All four test files are created by their owning plan's first task (RED phase of the task-level TDD loop). Existing conftest.py + pytest.ini cover shared fixtures; no conftest changes needed.*

---

## Manual-Only Verifications

| Behavior | Requirement | Why Manual | Test Instructions |
|----------|-------------|------------|-------------------|
| Manifest visible to a real LLM call in the running REPL | DISC-01 | Requires full harness startup (wiring is Phase 14); Phase 12 proves the seam at the `to_llm_messages()` unit level | Deferred to Phase 14 E2E: author a skill under `.agentharness/skills/`, start the REPL, inspect the first system block |

---

## Validation Sign-Off

- [x] All tasks have `<automated>` verify (each task ships its own test file)
- [x] Sampling continuity: no 3 consecutive tasks without automated verify
- [x] Wave 0 covers all MISSING references (4 test files + PyYAML install)
- [x] No watch-mode flags
- [x] Feedback latency < 15s
- [x] `nyquist_compliant: true` set in frontmatter

**Approval:** pending
