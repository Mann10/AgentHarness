---
phase: 13
slug: context-plumbing-persist-fix
status: draft
nyquist_compliant: false
wave_0_complete: false
created: 2026-08-01
---

# Phase 13 — Validation Strategy

> Per-phase validation contract for feedback sampling during execution.

---

## Test Infrastructure

| Property | Value |
|----------|-------|
| **Framework** | pytest 8.x + pytest-asyncio (`asyncio_mode = auto`) |
| **Config file** | `pytest.ini` (testpaths = tests) |
| **Quick run command** | `python -m pytest tests/test_persist.py -x` |
| **Full suite command** | `python -m pytest -q` |
| **Estimated runtime** | ~3 seconds (103 existing + ~8 new tests) |

---

## Sampling Rate

- **After every task commit:** Run `python -m pytest tests/test_persist.py -x`
- **After every plan wave:** Run `python -m pytest -q`
- **Before `/gsd-verify-work`:** Full suite must be green
- **Max feedback latency:** 5 seconds

---

## Per-task Verification Map

| task ID | Plan | Wave | Requirement | Threat Ref | Secure Behavior | Test Type | Automated Command | File Exists | Status |
|---------|------|------|-------------|------------|-----------------|-----------|-------------------|-------------|--------|
| 13-01-01 | 01 | 1 | ACT-03 | T-13-01 | persist flag on Message; bodies live in to_llm_messages | unit | `python -m pytest tests/test_persist.py::test_persist_false_message_in_llm_messages -x` | ❌ W0 | ⬜ pending |
| 13-01-02 | 01 | 1 | ACT-05 | T-13-01 | to_events filters persist=False | unit | `python -m pytest tests/test_persist.py::test_to_events_skips_persist_false -x` | ❌ W0 | ⬜ pending |
| 13-02-01 | 02 | 2 | ACT-05 | T-13-02 | mark_saved counts persisted only; round-trip clean | unit | `python -m pytest tests/test_persist.py::test_save_resume_no_skill_content -x` | ❌ W0 | ⬜ pending |
| 13-02-02 | 02 | 2 | ACT-05 | T-13-02 | repeated saves: no missing/duplicated events | unit | `python -m pytest tests/test_persist.py::test_repeated_saves_no_drift -x` | ❌ W0 | ⬜ pending |
| 13-03-01 | 03 | 3 | ACT-03/04 | T-13-03 | skill_state non-serialized; exemption documented | unit | `python -m pytest tests/test_persist.py::test_skill_state_never_serialized -x` | ❌ W0 | ⬜ pending |

*Status: ⬜ pending · ✅ green · ❌ red · ⚠️ flaky*

---

## Wave 0 Requirements

- [ ] `tests/test_persist.py` — persist-filter, index-drift, and JSONL-clean tests for ACT-03/04/05

*If none: "Existing infrastructure covers all phase requirements."*

---

## Manual-Only Verifications

| Behavior | Requirement | Why Manual | Test Instructions |
|----------|-------------|------------|-------------------|
| — | — | — | — |

*All phase behaviors have automated verification.*

---

## Validation Sign-Off

- [ ] All tasks have `<automated>` verify or Wave 0 dependencies
- [ ] Sampling continuity: no 3 consecutive tasks without automated verify
- [ ] Wave 0 covers all MISSING references
- [ ] No watch-mode flags
- [ ] Feedback latency < 5s
- [ ] `nyquist_compliant: true` set in frontmatter

**Approval:** {pending / approved 2026-08-01}
