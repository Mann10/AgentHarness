---
phase: 16
slug: tui-integration-skill-indicator
status: draft
nyquist_compliant: false
wave_0_complete: false
created: 2026-08-03
---

# Phase 16 — Validation Strategy

> Per-phase validation contract for feedback sampling during execution.
> Derived from `16-RESEARCH.md` §Validation Architecture (lines 527-571).

---

## Test Infrastructure

| Property | Value |
|----------|-------|
| **Framework** | pytest 8.4.2 (`asyncio_mode = auto`, `testpaths = tests`) for backend; `tsc --noEmit` + `tsup` for TUI (no TS test runner — Phase 11 precedent) |
| **Config file** | `pytest.ini`; `tui-ink/tsconfig.json` |
| **Quick run command** | Backend: `python -m pytest tests/test_skill_loaded_notification.py -x` · TUI: `npm run typecheck` (in `tui-ink/`) |
| **Full suite command** | `python -m pytest -q && npm run typecheck && npm run build` (build in `tui-ink/`) |
| **Estimated runtime** | ~15 seconds |

---

## Sampling Rate

- **After every task commit:** Run `python -m pytest tests/test_skill_loaded_notification.py -x` (backend tasks) or `npm run typecheck` (TUI tasks)
- **After every plan wave:** Run `python -m pytest -q && npm run typecheck && npm run build`
- **Before `/gsd-verify-work`:** Full suite must be green
- **Max feedback latency:** ~15 seconds

---

## Per-task Verification Map

| task ID | Plan | Wave | Requirement | Threat Ref | Secure Behavior | Test Type | Automated Command | File Exists | Status |
|---------|------|------|-------------|------------|-----------------|-----------|-------------------|-------------|--------|
| 16-01-01 | 01 | 1 | ACT-06 | T-16-01 / — | Event fires on real load; no event on no-op paths | unit/integration | `python -m pytest tests/test_skill_loaded_notification.py -k "emits or no_event" -x` | ✗ W0 | ○ pending |
| 16-01-02 | 01 | 1 | ACT-06 | T-16-02 / — | Wire format `{type:"skill_loaded", payload:{skill}}` only | unit | `python -m pytest tests/test_skill_loaded_notification.py -k "wire_format" -x` | ✗ W0 | ○ pending |
| 16-01-03 | 01 | 1 | ACT-06 | T-16-03 / — | RPC round trip emits notification; no pollution | integration | `python -m pytest tests/test_skill_loaded_notification.py -k "round_trip or pollution" -x` | ✗ W0 | ○ pending |
| 16-02-01 | 02 | 2 | ACT-06 | — | `/skill` intercept compiles with new types | typecheck | `npm run typecheck` (in `tui-ink/`) | ✓ (tsconfig) | ○ pending |
| 16-03-01 | 03 | 2 | ACT-06 | — | Chip + notices compile; no stream pollution | typecheck/build | `npm run typecheck && npm run build` (in `tui-ink/`) | ✓ | ○ pending |
| 16-03-02 | 03 | 2 | ACT-06 | — | Human E2E: `/skill` + chip round trip | human (blocking) | `npm run start` (in `tui-ink/`, manual — 11-04-03 pattern) | — | ○ pending |

*Status: ○ pending → ✓ green → ✗ red → ⚠ flaky*

---

## Wave 0 Requirements

- [ ] `tests/test_skill_loaded_notification.py` — stubs covering all five ACT-06 automated dimensions (event emission both paths, no-event on no-op paths, wire format, round trip, pollution); uses `_build_runtime` real-stack fixture pattern from `test_skills_e2e.py` and temp `skills_root` fixture from `test_skills_load_rpc.py`
- [ ] `tests/conftest.py` — no change needed (existing fixtures suffice)
- [ ] Framework install — none (pytest + asyncio_mode already configured)

---

## Manual-Only Verifications

| Behavior | Requirement | Why Manual | Test Instructions |
|----------|-------------|------------|-------------------|
| `/skill <name>` in TUI loads skill, shows notice + chip, never forwarded as prompt | ACT-06 SC-1 | No TS test runner; Ink 7.1.1 incompatible with ink-testing-library v4 | `npm run start` in `tui-ink/` → type `/skill demo-greeter` + Enter → `✓ Loaded skill demo-greeter` notice, chip appears, no assistant message starts; `/skills` + Enter → treated as chat text |
| Model-driven load shows chip, no notice, no stream pollution | ACT-06 SC-2/SC-4 | No TS test runner; requires live model turn | Model turn calling `read_skill` → chip gains the skill with no notice, no stream message, no tool card |
| Full keystroke → chip round trip | ACT-06 SC-3 | Visual end-to-end | Full keystroke → chip visual check via `npm run start` |

---

## Validation Sign-Off

- [ ] All tasks have `<automated>` verify or Wave 0 dependencies
- [ ] Sampling continuity: no 3 consecutive tasks without automated verify
- [ ] Wave 0 covers all MISSING references
- [ ] No watch-mode flags
- [ ] Feedback latency < 15s
- [ ] `nyquist_compliant: true` set in frontmatter

**Approval:** pending
