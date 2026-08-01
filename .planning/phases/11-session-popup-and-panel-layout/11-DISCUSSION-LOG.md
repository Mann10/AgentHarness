# Phase 11: Session Popup & Panel Layout - Discussion Log

> **Audit trail only.** Do not use as input to planning, research, or execution agents.
> Decisions are captured in CONTEXT.md — this log preserves the alternatives considered.

**Date:** 2026-07-31
**Phase:** 11-session-popup-and-panel-layout
**Areas discussed:** Panel Layout, /session popup, /new semantics, Date/time display

---

## Panel Layout

| Option | Description | Selected |
|--------|-------------|----------|
| Conversation left, date/time right | Left = conversation (main), right = date/time panel. Matches 09 UI-SPEC's right-side StatsPanel design. SessionPanel disappears. | ✓ |
| Date/time left, conversation right | Keep current arrangement, swap Sessions content for date/time. | |
| Date/time in header/footer instead | No separate panel; date/time lives in Header or Footer. | |

| Option | Description | Selected |
|--------|-------------|----------|
| Keep Header, session name in date/time panel | Header shows app name + session title; date/time panel also shows active session name. | ✓ |
| Remove Header | Maximal conversation space. | |
| Keep Header, clock-only panel | Date/time panel is clock-only. | |

| Option | Description | Selected |
|--------|-------------|----------|
| Keep ToolMonitorPanel | Bottom panel unchanged, appears only when tool calls active. | ✓ |
| Move tool calls inline, remove panel | Fold tool info into conversation flow. | |
| Remove tool monitoring | Tool info lost. | |

| Option | Description | Selected |
|--------|-------------|----------|
| Fixed width ~24-30 cols | Matches 09 UI-SPEC's 30-col StatsPanel. | ✓ |
| Auto width | Width adapts to content. | |
| Configurable width | Future settings command. | |

**User's choice:** Conversation left + date/time right; keep Header with session name also in date panel; keep ToolMonitorPanel; fixed ~24-30 col right panel.
**Notes:** SessionPanel (left list) is removed entirely — sessions live in the `/session` popup only.

---

## /session Popup

| Option | Description | Selected |
|--------|-------------|----------|
| Small popup near input bar | Overlay box near input, conversation visible behind. | |
| Full-screen overlay | Replaces app content, like 09 UI-SPEC SessionPicker. | ✓ |
| Inline in conversation | List rendered in conversation panel. | |

| Option | Description | Selected |
|--------|-------------|----------|
| Keyboard navigation | ↑/↓, Enter, Esc. Ink keyboard-first. | ✓ |
| Mouse-driven | GUI-like click selection. | |
| Both keyboard + mouse | Ink mouseEvents support. | |

| Option | Description | Selected |
|--------|-------------|----------|
| Title + id + msgs + age, recent first | Full row info, matches REPL /sessions output. | ✓ |
| Title only | Cleanest but hard to distinguish untitled sessions. | |
| Full detail incl. token count | Requires backend changes. | |

| Option | Description | Selected |
|--------|-------------|----------|
| Include create/delete/rename | Moves [n]/[d]/[r] hints into overlay. | |
| Switch-only | Create via /new; delete/rename out of scope. | ✓ |
| Create + delete only | Rename out of scope. | |

| Option | Description | Selected |
|--------|-------------|----------|
| Load history into view | New RPC method (sessions.get) returning session messages. | ✓ |
| Switch only, no history load | Conversation starts empty. | |

**User's choice:** Full-screen overlay; keyboard nav; rows = title + id + msgs + age recent-first; switch-only; loads conversation history on select.
**Notes:** History loading requires a new backend capability — no message-returning RPC method exists today; `JSONLSessionStore.load()` returns full session events.

---

## /new Semantics

| Option | Description | Selected |
|--------|-------------|----------|
| Immediate, auto-save current | Fresh conversation on Enter; current session auto-saved; no confirm. | ✓ |
| Confirm if unsaved | Prompt when unsaved content exists. | |
| Always confirm | Always ask. | |

| Option | Description | Selected |
|--------|-------------|----------|
| Use existing sessions.create | Calls RPC, switches, clears view. Auto-title from first prompt still applies. | ✓ |
| Add visible notice | 'New session started' notice in conversation view. | |
| Prompt for session name | Ask for a name first. | |

| Option | Description | Selected |
|--------|-------------|----------|
| Auto-title from first prompt | First prompt becomes session title (truncated to 50 chars), matching REPL. | ✓ |
| No auto-title, manual only | Stays 'untitled' until renamed. | |
| TUI keeps untitled, REPL unchanged | Mode-dependent behavior. | |

**User's choice:** Immediate fresh conversation on Enter (auto-save current, no confirm); calls existing `sessions.create`; auto-titles from first prompt.
**Notes:** User emphasized "/new + Enter should start a fresh conversation" — no confirmation step. Clarified that "auto-title from first prompt" means the REPL pattern (main.py:185-186) where the first prompt becomes the truncated session title.

---

## Date/Time Display

| Option | Description | Selected |
|--------|-------------|----------|
| Live clock (current date+time) | Updates every second. Reverses 09-CONTEXT D-29. | ✓ |
| Session timestamps | Shows session created/updated times. | |
| Live clock + session timestamps | Both. | |

| Option | Description | Selected |
|--------|-------------|----------|
| 24-hour HH:MM:SS | Common in terminals. | ✓ |
| 12-hour with AM/PM | Matches 09 UI-SPEC example. | |
| Include weekday | e.g. Thu Jul 31, 14:32:05. | |

| Option | Description | Selected |
|--------|-------------|----------|
| Date + time | Date above, time below, both prominent. | ✓ |
| Time only | Minimal. | |
| Time prominent, date dim | Time prominent. | |

**User's choice:** Live clock (current date+time) updating every second; 24-hour HH:MM:SS; both date and time shown.

---

## OpenCode's Discretion

- Overlay styling, row layout, date format string in the session picker
- `sessions.get` RPC method shape and TUI store history-ingestion mechanics
- Live clock implementation detail in Ink
- Scroll behavior after loading history
- Additional keyboard binding details

## Deferred Ideas

- Create/delete/rename sessions inside the `/session` overlay — switch-only for this phase
- Mouse-driven session picker — keyboard nav chosen
- Token count per session in the popup — needs backend changes
- Configurable right-panel width — fixed for now
