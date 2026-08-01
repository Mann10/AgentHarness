---
phase: 11-session-popup-and-panel-layout
plan: 04
subsystem: ui
tags: [ink, react, zustand, rpc, tui, layout, clock]

# Dependency graph
requires:
  - phase: 11-session-popup-and-panel-layout
    provides: "11-03 /session picker, /new command, footer hints; 11-01 backend sessions.get + auto-title"
provides:
  - "Conversation-first layout — SessionPanel removed (D-02), conversation owns the screen"
  - "DatePanel right companion: live 24h clock (HH:MM:SS) + ISO date + active session name (D-14/D-15/D-16)"
  - "Phase 11 end-to-end human verification"
affects: [None — final plan of Phase 11]

# Tech tracking
tech-stack:
  added: []
  patterns:
    - "Live clock via useEffect + setInterval(1000) — Ink 7.1 has no useInterval (research Pitfall 3)"
    - "Tick state confined inside DatePanel so 1 Hz re-renders never cascade to the streaming conversation"
    - "Panel hidden below 68 terminal columns (UI-SPEC §9 floor), conversation takes full width"

key-files:
  created: [tui-ink/src/panels/date-panel.tsx]
  modified: [tui-ink/src/app.tsx]
  deleted: [tui-ink/src/panels/session-panel.tsx]

key-decisions:
  - "DatePanel is passive (borderColor gray, NOT focusable, not wrapped in FocusablePanel) — UI-SPEC §6.1"
  - "Time line is bold (visual hero, UI-SPEC §4); date above, time below, then dim Session label + title (D-16 locks exactly date + time + session name)"
  - "SessionPanel deleted (D-02) — session identity moves into the /session overlay from Plan 03"

requirements-completed: [D-01, D-02, D-03, D-04, D-05, D-14, D-15, D-16]

# Metrics
duration: 15min
completed: 2026-08-01
---

# Phase 11 Plan 04: Conversation-First Layout + DatePanel + E2E Verification Summary

**Conversation owns the screen with a passive live-clock DatePanel on the right; the always-visible SessionPanel is gone; the phase is human-verified end-to-end.**

## Performance

- **Duration:** 15 min
- **Started:** 2026-08-01T13:05:00Z
- **Completed:** 2026-08-01T13:20:00Z
- **Tasks:** 3
- **Files modified:** 2 (+1 deleted)

## Accomplishments
- `DatePanel` component (new): 28-col passive right panel with live 24h clock (`HH:MM:SS`, bold), ISO date (`YYYY-MM-DD`) above, and dim `Session` label + active-session title; `useEffect` + `setInterval(1000)` tick confined inside the component; hidden below 68 terminal columns (tui-ink/src/panels/date-panel.tsx)
- App layout restructure: row Box is now conversation `FocusablePanel` + `<DatePanel />`; `SessionPanel` import and `id="sessions"` wrapper removed; `session-panel.tsx` deleted with zero references (grep-verified) (tui-ink/src/app.tsx)
- Focus cycle simplifies to conversation ↔ input (tool-monitor joins only while visible); Header/ToolMonitorPanel/Footer untouched

## Commits

1. `90cafdb` `feat(11-04): add DatePanel live-clock component` (tui-ink/src/panels/date-panel.tsx)
2. `5d90a72` `feat(11-04): conversation-first layout with DatePanel, remove SessionPanel` (tui-ink/src/app.tsx, session-panel.tsx deleted)

## Verification

- `npm run typecheck` → 0 errors; `npm run build` → success (tui-ink/)
- Grep gates: `DatePanel` import + render; no `SessionPanel` / `id="sessions"`; `session-panel.tsx` absent; `setInterval` in date-panel only
- Human E2E (task 11-04-03): 7-step checklist verified end-to-end — conversation-first layout, no Sessions panel, ticking 24h clock with date + session name, /session picker nav/select/close, history loads and streams, /new fresh start, tool monitor + header/footer intact (follow-up session-name fix delivered via quick task 260801-jra)

---
*Phase: 11-session-popup-and-panel-layout*
*Completed: 2026-08-01*
