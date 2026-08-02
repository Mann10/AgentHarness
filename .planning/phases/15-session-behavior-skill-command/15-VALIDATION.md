---
phase: 15
slug: session-behavior-skill-command
status: draft
nyquist_compliant: false
wave_0_complete: false
created: 2026-08-02
---

# Phase 15 — Validation Strategy

> Per-phase validation contract for feedback sampling during execution.

---

## Test Infrastructure

| Property | Value |
|----------|-------|
| **Framework** | pytest 7.x + pytest-asyncio (`asyncio_mode = auto`) |
| **Config file** | `pytest.ini` (testpaths = tests) |
| **Quick run command** | `python -m pytest tests/test_skills_load_rpc.py tests/test_load_skill.py tests/test_skill_command.py tests/test_skills_filter.py -q` |
| **Full suite command** | `python -m pytest -q` |
| **Estimated runtime** | ~20-40 seconds |

---

## Sampling Rate

- **After every task commit:** Run `python -m pytest <touched test files> -q`
- **After every plan wave:** Run `python -m pytest -q`
- **Before `/gsd-verify-work`:** Full suite must be green
- **Max feedback latency:** ~40 seconds

---

## Per-task Verification Map

| task ID | Plan | Wave | Requirement | Threat Ref | Secure Behavior | Test Type | Automated Command | File Exists | Status |
|---------|------|------|-------------|------------|-----------------|-----------|-------------------|-------------|--------|
| 15-01-01 | 01 | 1 | ACT-01 | T-15-01 | RPC params validated; structured error codes | unit | `python -m pytest tests/test_skills_load_rpc.py -q` | ❌ W0 | ⬜ pending |
| 15-01-02 | 01 | 1 | ACT-01 | T-15-01 | skills.load registered in 4 layers | unit+tsc | `python -m pytest tests/test_rpc_adapter.py -q`; `cd tui-ink && npm run typecheck` | ❌ W0 | ⬜ pending |
| 15-02-01 | 02 | 1 | ACT-01 | T-15-02 | /skill branches: ack / not-found / usage; never falls through | unit | `python -m pytest tests/test_skill_command.py -q` | ❌ W0 | ⬜ pending |
| 15-03-01 | 03 | 2 | ACT-01 | — | token cache + cap refusal with no partial state | unit | `python -m pytest tests/test_load_skill.py -q` | ✅ exists | ⬜ pending |
| 15-03-02 | 03 | 2 | ACT-01 | — | CAP-04 intersection contract pure fn | unit | `python -m pytest tests/test_skills_filter.py -q` | ❌ W0 | ⬜ pending |

*Status: ⬜ pending · ✅ green · ❌ red · ⚠️ flaky*

---

## Wave 0 Requirements

- [ ] `tests/test_skills_load_rpc.py` — RPC adapter + dispatcher + protocol tests for `skills.load`
- [ ] `tests/test_skill_command.py` — REPL `_handle_session_cmd` /skill branch tests
- [ ] `tests/test_skills_filter.py` — `intersect_allowed_tools` contract tests

*Existing infrastructure (test_load_skill.py fixtures, test_rpc_adapter.py patterns) covers the rest.*

---

## Manual-Only Verifications

| Behavior | Requirement | Why Manual | Test Instructions |
|----------|-------------|------------|-------------------|
| REPL `/skill` end-to-end ack flow | ACT-01 | Interactive REPL loop + stdout ack feel | `python main.py` → `/skill demo-greeter` (prints ack) → `/skill demo-greeter` again (prints "already loaded") → `/skill nosuch` (prints not-found) → `/skill` (prints usage) |

*All other phase behaviors have automated verification.*

---

## Validation Sign-Off

- [ ] All tasks have `<automated>` verify or Wave 0 dependencies
- [ ] Sampling continuity: no 3 consecutive tasks without automated verify
- [ ] Wave 0 covers all MISSING references
- [ ] No watch-mode flags
- [ ] Feedback latency < 40s
- [ ] `nyquist_compliant: true` set in frontmatter

**Approval:** pending
