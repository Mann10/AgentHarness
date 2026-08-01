---
phase: 14
slug: read-skill-provider-e2e
status: draft
nyquist_compliant: false
wave_0_complete: false
created: 2026-08-01
---

# Phase 14 — Validation Strategy

> Per-phase validation contract for feedback sampling during execution.

---

## Test Infrastructure

| Property | Value |
|----------|-------|
| **Framework** | pytest 8.x + pytest-asyncio (auto mode) |
| **Config file** | `pytest.ini` — `asyncio_mode = auto`, `testpaths = tests` |
| **Quick run command** | `python -m pytest tests/test_skills_store.py tests/test_skills_provider.py tests/test_load_skill.py tests/test_cancel_mid_gather.py -x` |
| **Full suite command** | `python -m pytest -q` |
| **Estimated runtime** | ~30-60 seconds (full suite currently 103 tests) |

---

## Sampling Rate

- **After every task commit:** Run `python -m pytest tests/test_<plan_owned_file>.py -x`
- **After every plan wave:** Run `python -m pytest -q`
- **Before `/gsd-verify-work`:** Full suite must be green
- **Max feedback latency:** 60 seconds

---

## Per-task Verification Map

| task ID | Plan | Wave | Requirement | Threat Ref | Secure Behavior | Test Type | Automated Command | File Exists | Status |
|---------|------|------|-------------|------------|-----------------|-----------|-------------------|-------------|--------|
| 14-01-01 | 01 | 1 | DISC-03, DISC-04, DISC-05 | T-14-02 | SkillStore index + load; traversal-guarded read_path rejects all escape vectors | unit | `python -m pytest tests/test_skills_store.py -x` | ✗ W0 | ⏳ pending |
| 14-01-02 | 01 | 1 | DISC-04, DISC-05, CAP-01 | T-14-02 | win32 + posix traversal vectors (`../`, `..\`, absolute, symlink/junction) rejected | unit | `python -m pytest tests/test_skills_store.py -x` | ✗ W0 | ⏳ pending |
| 14-02-01 | 02 | 1 | DISC-03, CAP-03 | T-14-01 | Async SkillToolProvider with two tools; reserved-name collision rejected | unit | `python -m pytest tests/test_skills_provider.py -x` | ✗ W0 | ⏳ pending |
| 14-02-02 | 02 | 1 | CAP-03 | T-14-01 | filter retention contract: `allowed ∪ {read_skill, read_skill_path}` always retained | unit | `python -m pytest tests/test_skills_provider.py -x` | ✗ W0 | ⏳ pending |
| 14-03-01 | 03 | 2 | DISC-03, ACT-02 | T-14-05 | `add_skill_message` persist=False + skill_name tag; body in system message, not tool result | unit | `python -m pytest tests/test_load_skill.py -x` | ✗ W0 | ⏳ pending |
| 14-03-02 | 03 | 2 | DISC-03, ACT-02, D-07/D-09 | T-14-05 | `RuntimeAPI.load_skill` single shared path; dedup no-op; skill_state["loaded"] written | unit | `python -m pytest tests/test_load_skill.py -x` | ✗ W0 | ⏳ pending |
| 14-03-03 | 03 | 2 | ACT-02, DISC-03 | T-14-01 | main.py production wiring: manifest attach + `__skills__` provider registration + reserved-name assert | unit | `python -m pytest -q` | ✗ W0 | ⏳ pending |
| 14-04-01 | 04 | 3 | ACT-02, CAP-01 | T-14-04 | Cancel-mid-gather: no partial tool messages, no dangling tool_calls next turn | unit | `python -m pytest tests/test_cancel_mid_gather.py -x` | ✗ W0 | ⏳ pending |
| 14-04-02 | 04 | 3 | DISC-03..05, ACT-02, CAP-01, CAP-03 | T-14-02..05 | Backend E2E: load → inject → summarize-survive → JSONL untouched | unit/e2e | `python -m pytest tests/test_load_skill.py tests/test_cancel_mid_gather.py -x` | ✗ W0 | ⏳ pending |

*Status: ⏳ pending | ✅ green | ❌ red | ⚠️ flaky*

---

## Wave 0 Requirements

- [ ] `tests/test_skills_store.py` — stubs for DISC-04/DISC-05 (SkillStore traversal suite)
- [ ] `tests/test_skills_provider.py` — stubs for DISC-03/CAP-03 (provider + filter contract)
- [ ] `tests/test_load_skill.py` — stubs for DISC-03/ACT-02 (load path + injection)
- [ ] `tests/test_cancel_mid_gather.py` — stub for D-14 (cancel cleanup regression)
- [ ] `tests/conftest.py` — skill-dir fixtures (`tmp_path` based), shared where possible

*If none: "Existing infrastructure covers all phase requirements."* — not the case here; 4 new test files.

---

## Manual-Only Verifications

| Behavior | Requirement | Why Manual | Test Instructions |
|----------|-------------|------------|-------------------|
| None — all phase behaviors have automated verification (D-15: backend-only E2E in Python) | — | — | — |

---

## Validation Sign-Off

- [ ] All tasks have `<automated>` verify or Wave 0 dependencies
- [ ] Sampling continuity: no 3 consecutive tasks without automated verify
- [ ] Wave 0 covers all MISSING references
- [ ] No watch-mode flags
- [ ] Feedback latency < 60s
- [ ] `nyquist_compliant: true` set in frontmatter

**Approval:** pending
