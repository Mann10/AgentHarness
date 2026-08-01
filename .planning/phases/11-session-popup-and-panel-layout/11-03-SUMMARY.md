---
phase: 11-session-popup-and-panel-layout
plan: 03
subsystem: ui
tags: [ink, react, zustand, rpc, tui, session-picker, slash-commands]

# Dependency graph
requires:
  - phase: 11-session-popup-and-panel-layout
    provides: "11-02 SessionMessage/SessionHistoryResponse types, getSessionHistory RPC client method, loadConversation store action"
  - phase: 11-session-popup-and-panel-layout
    provides: "11-01 sessions.get backend RPC, context-restore fix, auto-title"
provides:
  - "Full-screen switch-only SessionPicker overlay (key trap via conditional render)"
  - "/session and /new slash-command interception in InputBar"
  - "App-level q-quit gating while picker is open"
  - "Honest footer hint set (real commands only)"
affects: [11-04 layout restructure (SessionPanel removal, DatePanel)]

# Tech tracking
tech-stack:
  added: []
  patterns:
    - "Full-screen overlay via conditional render (picker replaces main tree -> its useInput is the only active handler)"
    - "Module-level design tokens (ACCENT/CURSOR/HINT_LINE) - no raw literals in JSX (UI-SPEC 10)"
    - "Windowed scroll list: rows.slice(offset, offset+visibleCount) with visibleCount from useWindowSize"
    - "clamp cursor, no wrap; Esc AND q both close (picker owns q while open)"

key-files:
  created: [tui-ink/src/components/session-picker.tsx]
  modified: [tui-ink/src/app.tsx, tui-ink/src/components/footer.tsx]

key-decisions:
  - "q closes the picker (owned inside SessionPicker useInput) while App-level quit handler early-returns on pickerOpen (research Pitfall 2)"
  - "/new is immediate: createSession -> setActiveSession -> resetConversation, no confirm (D-11/D-12)"
  - "Footer drops aspirational [/] search and [1-3] jump hints - only real commands listed"
  - "Active session marked with single green dot, cursor row bold blue accent - no glyph on every row (UI-SPEC 1)"

patterns-established:
  - "Slash-command interception: /session (open overlay), /new (fresh start), /sessions (kept legacy)"
  - "Overlay lifecycle: mount fetches listSessions + seeds store; select = switchSession -> getSessionHistory -> setActiveSession + loadConversation"

requirements-completed: [D-06, D-07, D-08, D-09, D-11, D-12]

# Metrics
duration: 3min
completed: 2026-08-01
---

# Phase 11 Plan 03: /session Overlay + /new Command Summary

**Full-screen switch-only SessionPicker overlay opened by /session, immediate /new fresh-chat command, and honest footer hints — all driven by the Wave-1 contracts (getSessionHistory RPC client, loadConversation store action, SessionMessage types)**

## Performance

- **Duration:** 3 min
- **Started:** 2026-08-01T12:57:16Z
- **Completed:** 2026-08-01T13:00:06Z
- **Tasks:** 3
- **Files modified:** 3

## Accomplishments
- `SessionPicker` full-screen overlay: blue `$accent` border, keyboard-first (↑/↓ clamped cursor, Enter selects, Esc AND q close), rows sorted `updated_at` desc showing title/8-char id/msg count/relative age, windowed scroll keeping cursor visible, switch-only (no create/delete/rename)
- Select flow: `switchSession` → `getSessionHistory` → `setActiveSession` + `loadConversation`, with loading/empty/error/switching states and failure handling (picker stays open, red error line, T-11-05 mitigated)
- App wiring: `pickerOpen` state, conditional full-screen render (true key trap — InputBar unmounts), App `q`-quit handler gated by `pickerOpen` (T-11-07 mitigated)
- InputBar `/session` (open overlay) + `/new` (create + activate + reset conversation, no confirm, D-11/D-12) branches alongside legacy `/sessions`
- Footer now lists only real commands: `[?] help  [/session] sessions  [/new] new chat  [Tab] panels  [q] quit`

## task Commits

Each task was committed atomically:

1. **task 1: SessionPicker full-screen overlay component** - `2497d35` (feat)
2. **task 2: App wiring — picker state, conditional render, q-gate, InputBar /session + /new branches** - `3599c98` (feat)
3. **task 3: honest footer hints** - `0b2699f` (feat)

**Plan metadata:** `pending` (docs: complete plan)

## Files Created/Modified
- `tui-ink/src/components/session-picker.tsx` - Full-screen switch-only overlay: list/loading/empty/error/switching states, keyboard nav, windowed scroll, `switchSession`→`getSessionHistory`→store-seed select flow (new)
- `tui-ink/src/app.tsx` - `pickerOpen` state, conditional `<SessionPicker>` render, q-quit gate, InputBar `onOpenPicker` prop + `/session` `/new` branches (modified)
- `tui-ink/src/components/footer.tsx` - Real-commands-only hint set, aspirational hints removed (modified)

## Decisions Made
- `q` close is handled INSIDE the picker's own `useInput`; the App-level quit handler early-returns while the picker is open — per research Pitfall 2 this is the only way `q` closes the picker instead of quitting the app (T-11-07)
- `/new` resolves `createSession` → `setActiveSession(id)` → `resetConversation()` with no confirm prompt; unhandled `createSession` rejection accepted by design (T-11-08, matches legacy `/sessions` error behavior)
- SessionPicker sorts by `updated_at` desc and computes age from `updated_at` (research Pitfall 5 — glob order is not recency order)
- Rows windowed via `rows.slice(scrollOffset, scrollOffset + visibleCount)` — never renders the full list (T-11-06)

## Deviations from Plan

None - plan executed exactly as written.

## Issues Encountered
- None. All interfaces declared in the plan's `<interfaces>` block (getSessionHistory, loadConversation, SessionMessage, FocusablePanel, InputBar) matched the installed code; `npm run typecheck` and `npm run build` passed on the first run for every task.

## User Setup Required

None - no external service configuration required.

## Next Phase Readiness
- Ready for **11-04** (layout restructure): SessionPanel removal (D-02), DatePanel with live clock (D-14/D-15/D-16), conversation main panel (D-01). The picker and commands are already wired; 11-04 needs to drop the `sessions` FocusablePanel + SessionPanel usage in `app.tsx` and add the right-side date/time panel (rendered when width ≥ 68 per UI-SPEC §9).
- Note for 11-04: `InputBar`'s `onOpenPicker` prop and `App`'s `pickerOpen` state are now the established overlay pattern to keep.

---
*Phase: 11-session-popup-and-panel-layout*
*Completed: 2026-08-01*

## Self-Check: PASSED

- FOUND: `tui-ink/src/components/session-picker.tsx`
- FOUND: `.planning/phases/11-session-popup-and-panel-layout/11-03-SUMMARY.md`
- FOUND (git log): `2497d35`, `3599c98`, `0b2699f` — all three task commits exist
- `npm run typecheck`: exit 0 (tui-ink/)
- `npm run build`: Build success (tui-ink/)
