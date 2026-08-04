---
phase: 05
slug: harness-runtime
status: draft
nyquist_compliant: false
wave_0_complete: false
created: 2026-07-25
---

# Phase 5 — Validation Strategy

> Per-phase validation contract for feedback sampling during execution.

---

## Test Infrastructure

| Property | Value |
|----------|-------|
| **Framework** | pytest + pytest-asyncio |
| **Config file** | `pytest.ini` (Wave 0 creates) |
| **Quick run command** | `python -m pytest tests/ -x -q` |
| **Full suite command** | `python -m pytest tests/ -v` |
| **Estimated runtime** | ~30 seconds |

---

## Sampling Rate

- **After every task commit:** Run `python -m pytest tests/ -x -q`
- **After every plan wave:** Run `python -m pytest tests/ -v`
- **Before `/gsd-verify-work`:** Full suite must be green
- **Max feedback latency:** 30 seconds

---

## Per-task Verification Map

| task ID | Plan | Wave | Requirement | Threat Ref | Secure Behavior | Test Type | Automated Command | File Exists | Status |
|---------|------|------|-------------|------------|-----------------|-----------|-------------------|-------------|--------|
| 05-00-01 | 00 | 0 | — | — | N/A | infra | `python -m pytest tests/ -x -q` | ❌ W0 | ⬜ pending |
| 05-00-02 | 00 | 0 | — | — | N/A | infra | `python -c "import pytest"` | ❌ W0 | ⬜ pending |
| 05-01-01 | 01 | 1 | D-05, D-07 | — | N/A | unit | `pytest tests/test_event_bus.py -x -q` | ❌ W0 | ⬜ pending |
| 05-01-02 | 01 | 1 | D-07 | — | N/A | unit | `pytest tests/test_events.py -x -q` | ❌ W0 | ⬜ pending |
| 05-01-03 | 01 | 1 | D-07 | — | N/A | unit | `pytest tests/test_cancellation.py -x -q` | ❌ W0 | ⬜ pending |
| 05-02-01 | 02 | 1 | D-02 | — | N/A | unit | `pytest tests/test_session_manager.py -x -q` | ❌ W0 | ⬜ pending |
| 05-03-01 | 03 | 2 | D-03 | — | N/A | unit | `pytest tests/test_agent_events.py -x -q` | ❌ W0 | ⬜ pending |
| 05-04-01 | 04 | 2 | D-09, D-11, D-15 | T-05-09 | CancelledError re-raised | unit | `pytest tests/test_scheduler.py -x -q` | ❌ W0 | ⬜ pending |
| 05-05-01 | 05 | 3 | D-13 | — | N/A | unit | `pytest tests/test_runtime.py -x -q` | ❌ W0 | ⬜ pending |
| 05-06-01 | 06 | 4 | D-01, D-14 | — | N/A | integration | Manual — Textual app | ❌ W0 | ⬜ pending |
| 05-07-01 | 07 | 5 | D-02, D-12, D-13 | — | N/A | unit | `python -c "from harness import RuntimeAPI; print('ok')"` | ❌ W0 | ⬜ pending |

*Status: ⬜ pending · ✅ green · ❌ red · ⚠️ flaky*

---

## Wave 0 Requirements

- [ ] `tests/conftest.py` — shared fixtures (EventBus, StubAgent)
- [ ] `pytest.ini` — pytest configuration
- [ ] pytest + pytest-asyncio already in requirements.txt

---

## Manual-Only Verifications

| Behavior | Requirement | Why Manual | Test Instructions |
|----------|-------------|------------|-------------------|
| TUI subscribes to EventBus on mount | D-14 | Textual requires running app | Launch with `python main.py --tui`, verify prompt processing |
| TUI renders "grinding..." indicator | D-14 | Visual — requires human | Launch, submit prompt, observe indicator appears and clears |

*If none: "All phase behaviors have automated verification."*

---

## Validation Sign-Off

- [ ] All tasks have `<automated>` verify or Wave 0 dependencies
- [ ] Sampling continuity: no 3 consecutive tasks without automated verify
- [ ] Wave 0 covers all MISSING references
- [ ] No watch-mode flags
- [ ] Feedback latency < 30s
- [ ] `nyquist_compliant: true` set in frontmatter

**Approval:** pending
