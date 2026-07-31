---
phase: 11
slug: session-popup-and-panel-layout
status: draft
nyquist_compliant: false
wave_0_complete: true
created: 2026-07-31
---

# Phase 11 — Validation Strategy

> Per-phase validation contract for feedback sampling during execution.

---

## Test Infrastructure

| Property | Value |
|----------|-------|
| **Framework** | pytest (Python backend) + tsc/tsup (TUI typecheck/build) |
| **Config file** | `pytest.ini` (asyncio_mode = auto, testpaths = tests) |
| **Quick run command** | `python -m pytest -q` |
| **Full suite command** | `python -m pytest -q && npm run typecheck && npm run build` (in `tui-ink/`) |
| **Estimated runtime** | ~30 seconds (43 existing tests + new backend tests) |

---

## Sampling Rate

- **After every task commit:** Run `python -m pytest -q` (backend tasks) or `npm run typecheck` (TUI tasks)
- **After every plan wave:** Run full suite (pytest + typecheck + build)
- **Before `/gsd-verify-work`:** Full suite must be green
- **Max feedback latency:** 60 seconds

---

## Per-task Verification Map

| task ID | Plan | Wave | Requirement | Threat Ref | Secure Behavior | Test Type | Automated Command | File Exists | Status |
|---------|------|------|-------------|------------|-----------------|-----------|-------------------|-------------|--------|
| 11-01-01 | 01 | 1 | D-10 (sessions.get RPC) | T-11-01 / — | History payload is pure read; no active-session mutation | unit | `python -m pytest tests/test_runtime.py tests/test_session_manager.py -q` | ✅ | ⬜ pending |
| 11-01-02 | 01 | 1 | D-06/D-10 (switch restore fix) | T-11-01 / — | Loaded session restored before Agent creation; missing id → False | unit | `python -m pytest tests/test_runtime.py -q` | ✅ | ⬜ pending |
| 11-01-03 | 01 | 1 | D-13 (auto-title) | — | Title set from first prompt (≤50 chars + "..." suffix) on untitled session | unit | `python -m pytest tests/test_runtime.py -q` | ✅ | ⬜ pending |
| 11-02-01 | 02 | 2 | D-06/D-07/D-08/D-09 (picker) | — | Type-safe picker component; no keyboard double-handling | typecheck | `npm run typecheck` (in `tui-ink/`) | ✅ | ⬜ pending |
| 11-02-02 | 02 | 2 | D-11/D-12 (new command) | — | InputBar `/new` branch calls createSession + resets store | typecheck | `npm run typecheck` (in `tui-ink/`) | ✅ | ⬜ pending |
| 11-03-01 | 03 | 2 | D-01/D-03/D-04/D-05/D-14/D-15/D-16 (layout + clock) | — | DatePanel renders; SessionPanel removed; layout compiles | typecheck + build | `npm run typecheck && npm run build` (in `tui-ink/`) | ✅ | ⬜ pending |
| 11-04-01 | 04 | 3 | D-06..D-16 (end-to-end) | — | Full flow verified by human | manual checkpoint | `npm run start` (in `tui-ink/`, manual) | ✅ | ⬜ pending |

*Status: ⬜ pending · ✅ green · ❌ red · ⚠️ flaky*

---

## Wave 0 Requirements

- [ ] `tests/test_runtime.py` — extend with switch-restore + auto-title + history tests (existing fixture `runtime` covers DI)
- [ ] `tests/test_session_manager.py` — extend with `get_session` (pure read, no active-switch) test
- [ ] `tui-ink/tsconfig.json` — exists; typecheck gate ready

*Wave 0 requires no new infrastructure — pytest + tsc/tsup already configured.*

---

## Manual-Only Verifications

| Behavior | Requirement | Why Manual | Test Instructions |
|----------|-------------|------------|-------------------|
| `/session` opens full-screen overlay picker | D-06 | Visual/keyboard interaction; Ink overlay behavior not unit-testable (no TUI test infra) | `cd tui-ink && npm run start` → type `/session` + Enter → picker covers screen; ↑/↓ move cursor; Enter continues selected session and loads its history into the conversation; Esc closes with state preserved |
| Picker rows show title, 8-char id, message count, relative age, sorted most-recent first | D-08 | Visual layout + data correctness in terminal | Same session; inspect rows vs `python main.py` → `/sessions` output for same store |
| `/new` starts a fresh conversation, no confirm | D-11/D-12 | Interactive flow | Type `/new` + Enter → conversation cleared, header shows new untitled session |
| Date/time panel: date + `HH:MM:SS` ticking every second, active session name | D-14/D-15/D-16 | Live behavior, visual | Observe right panel for 5+ seconds; clock advances; name matches header |
| Layout: conversation main left, date/time right (~24-30 cols), no Sessions panel, header/footer intact, ToolMonitor still bottom | D-01/D-02/D-03/D-04/D-05 | Visual layout | Resize terminal to 80×24 and a 60-col split; panels must not break |
| History loading doesn't break streaming | D-10 | Integration | Continue a session with history → send a new prompt → tokens stream normally |

---

## Validation Sign-Off

- [ ] All tasks have `<automated>` verify or Wave 0 dependencies
- [ ] Sampling continuity: no 3 consecutive tasks without automated verify
- [ ] Wave 0 covers all MISSING references
- [ ] No watch-mode flags
- [ ] Feedback latency < 60s
- [ ] `nyquist_compliant: true` set in frontmatter

**Approval:** pending

---

*Phase: 11-session-popup-and-panel-layout*
*Validation strategy created: 2026-07-31*
