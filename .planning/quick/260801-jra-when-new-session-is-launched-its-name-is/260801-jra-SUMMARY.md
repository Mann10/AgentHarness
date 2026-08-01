---
quick_id: 260801-jra
slug: when-new-session-is-launched-its-name-is
subsystem: sessions-tui
tags: [sessions, auto-title, ink, rpc, tui]

# Dependency graph
requires:
  - phase: 11-session-popup-and-panel-layout
    provides: "11-01 auto-title (D-13) in submit_prompt, sessions.get RPC; 11-02 TUI contracts; 11-03 /session picker + /new"
provides:
  - "Auto-title persisted synchronously in submit_prompt — immediate list_sessions returns the real name"
  - "TUI refreshes sessions after /new and after each submit — panel/header/date-panel titles update without a manual switch"
  - "TUI binds the runtime's active session on connect via new sessions.active RPC"

# Tech tracking
tech-stack:
  added: ["sessions.active RPC method"]
  patterns:
    - "Persist derived session metadata at mutation time, not on_turn_complete"
    - "RPC surface: add a read-only handler + whitelist entry + client method + startup binding"

key-files:
  created: []
  modified: [harness/runtime.py, tests/test_runtime.py, tests/test_rpc_adapter.py, tui-ink/src/app.tsx, tui-ink/src/bridge/rpc-client.ts, backend/rpc/adapter.py, backend/rpc/protocol.py]

key-decisions:
  - "Backend persists auto-title in submit_prompt before scheduler dispatch (no turn-complete race)"
  - "TUI refreshSessions() helper chained after /new and after submitPrompt resolution"
  - "New sessions.active RPC returns runtime's active session id so the TUI binds it on connect (fixes 'No session'/'untitled' on cold start)"

requirements-completed: [D-11, D-12, D-13]

# Metrics
duration: 2h
completed: 2026-08-01
---

# Quick Task 260801-jra: Show Session Name in Panel on First Question

**When a new session is launched its name is not reflected in the conversation panel unless the user switches sessions — fixed so the panel/header/date-panel show the truncated auto-title as soon as the first question is asked.**

## Performance

- **Duration:** ~2 h
- **Started:** 2026-08-01T09:05:00Z
- **Completed:** 2026-08-01T11:30:00Z
- **Commits:** 3

## Accomplishments

- Backend: `submit_prompt` now persists the derived auto-title synchronously (after `session.title = derive_title(prompt)`, before scheduler dispatch) so an immediate `sessions.list` reads the title from disk instead of `None` — regression test `test_submit_prompt_title_persists_to_store` no longer sleeps (harness/runtime.py, tests/test_runtime.py)
- TUI: `refreshSessions()` helper chains `client.listSessions()` after `/new` and after each `submitPrompt(trimmed)` — panel/header/date-panel titles update without a manual session switch (tui-ink/src/app.tsx)
- Root-cause follow-up: cold-start TUI never knew the backend-created active session — added `sessions.active` RPC (`backend/rpc/adapter.py` + whitelist in `backend/rpc/protocol.py`), client `getActiveSession()` (`rpc-client.ts`), and startup binding in `App` (`app.tsx`) so the header shows the real session name instead of "No session" and panels show the title instead of "untitled"
- Human E2E verified via OCR: after the first question the header/panels show the auto-title without switching sessions

## Commits

1. `e22128f` `fix(sessions): persist auto-title synchronously in submit_prompt` (harness/runtime.py, tests/test_runtime.py)
2. `aa67827` `fix(tui): refresh sessions after /new and after each submitPrompt` (tui-ink/src/app.tsx)
3. `1df0660` `fix(tui): bind active session on connect so panels show real name` (backend/rpc/adapter.py, backend/rpc/protocol.py, tui-ink/src/app.tsx, tui-ink/src/bridge/rpc-client.ts, tests/test_rpc_adapter.py)

## Verification

- `python -m pytest -q` → 63 passed (incl. no-sleep title-persists regression + 3 new sessions.active tests)
- `npm run typecheck` (tui-ink/) → 0 errors; `npm run build` → success
- Grep gates: `submitPrompt(trimmed).then` in app.tsx; `save_session()` in runtime.py submit_prompt; `sessions.active` registered in adapter + whitelisted in protocol.py
- Human E2E: OCR-verified panel shows the auto-title on the first question; startup header shows the real session name

---
*Quick task: 260801-jra-when-new-session-is-launched-its-name-is*
*Completed: 2026-08-01*
