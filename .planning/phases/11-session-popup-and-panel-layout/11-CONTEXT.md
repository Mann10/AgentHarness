# Phase 11: Session Popup & Panel Layout - Context

**Gathered:** 2026-07-31
**Status:** Ready for planning

<domain>
## Phase Boundary

Reorganize the TypeScript Ink TUI (`tui-ink/`) so the conversation is the main panel with a date/time companion panel. Session management moves out of the always-visible left Sessions panel into prompt-input commands: `/session` opens a full-screen session picker overlay (select one to continue it), `/new` starts a fresh conversation. The JSON-RPC backend is extended only where needed to support loading a session's conversation history into the TUI.

</domain>

<decisions>
## Implementation Decisions

### Panel layout
- **D-01:** Conversation is the main (left) panel; the right panel shows date/time. Matches the right-side StatsPanel concept from the 09 UI-SPEC.
- **D-02:** The always-visible left **SessionPanel is removed** — session identity moves out of a persistent sidebar.
- **D-03:** Header is kept (shows app name + active session title, as today). The active session name is ALSO shown in the date/time panel.
- **D-04:** Bottom ToolMonitorPanel is kept unchanged (appears only when tool calls are active).
- **D-05:** Right date/time panel uses a fixed width (~24–30 columns).

### /session popup
- **D-06:** Typing `/session` in the prompt input and pressing Enter opens a **full-screen overlay** session picker (not a small dropdown).
- **D-07:** Navigation is keyboard-first: `↑`/`↓` move cursor, `Enter` selects (continues the session), `Esc` closes. Matches the 09 UI-SPEC SessionPicker navigation model.
- **D-08:** Each row shows: session title, short id (8 chars), message count, and relative age (e.g. "2h ago"). Sorted most-recent first.
- **D-09:** The popup is **switch-only** — no create/delete/rename inside the overlay.
- **D-10:** Selecting a session loads that session's past conversation history into the TUI conversation view. Requires a new backend capability (e.g. `sessions.get` RPC method returning session messages) — none exists today; the `JSONLSessionStore.load()` already returns full session events.

### /new semantics
- **D-11:** Typing `/new` and pressing Enter immediately starts a fresh conversation. Current session is auto-saved first (JSONL persists per turn, so unsaved work is minimal). No confirm prompt.
- **D-12:** `/new` calls the existing `sessions.create` RPC method, switches the active session, and clears the conversation view.
- **D-13:** New sessions auto-title from their first prompt (matching the REPL behavior in `main.py` lines 185-186), so "untitled" becomes the first prompt truncated to 50 chars after the first exchange.

### Date/time panel
- **D-14:** The panel shows a **live clock** — current date + current time, updating every second. Reverses 09-CONTEXT D-29 which deferred the clock.
- **D-15:** Time uses 24-hour format `HH:MM:SS`.
- **D-16:** Both date and time are shown (date above, time below). Active session name also displayed (per D-03).

### OpenCode's Discretion
- Exact overlay border/title styling and row layout in the session picker
- Date format string (e.g. "Jul 31, 2026" vs "2026-07-31")
- `sessions.get` RPC method shape, payload fields, and how the TUI store ingests loaded history
- Live clock implementation detail in Ink (useInterval vs setInterval), respecting Ink's re-render model
- Scroll/auto-scroll behavior after loading history into the conversation view
- Keyboard binding details beyond Enter/Esc/arrows

</decisions>

<canonical_refs>
## Canonical References

**Downstream agents MUST read these before planning or implementing.**

### Frontend (primary work area)
- `tui-ink/src/app.tsx` — App layout, InputBar (handles `/sessions` only today, line 39), FocusablePanel wiring
- `tui-ink/src/components/header.tsx` — Header showing session title + model + status (kept per D-03)
- `tui-ink/src/components/footer.tsx` — Footer hints (may need updating if `[1-3] jump` refers to panels that change)
- `tui-ink/src/panels/session-panel.tsx` — SessionPanel to be REMOVED (D-02)
- `tui-ink/src/panels/conversation-panel.tsx` — Conversation view (main panel)
- `tui-ink/src/panels/tool-monitor-panel.tsx` — ToolMonitorPanel (kept per D-04)
- `tui-ink/src/bridge/rpc-client.ts` — RPC client; existing `sessions.list/switch/create/delete` (lines 111-133); needs new history method
- `tui-ink/src/store/agent-store.ts` — Zustand store; `resetConversation`, `conversation`, `sessions` state
- `tui-ink/src/types.ts` — `SessionSummary`, `Message` types

### Backend (history loading support)
- `backend/rpc/adapter.py` — RPC method registration (7 methods today); add `sessions.get`-style handler
- `backend/rpc/dispatcher.py` — Pure routing; no business logic
- `session/store.py` — `JSONLSessionStore.load()` returns full session with events (line 60)
- `session/models.py` — `Session.to_events()` (line 58), `SessionSummary` (line 15)
- `harness/runtime.py` — `list_sessions`/`switch_session`/`create_session`/`delete_session` (lines 90-126)

### Design contract
- `.planning/phases/09-ts-tui-json-rpc/09-UI-SPEC.md` — SessionPicker overlay spec (§3), StatsPanel Date/Time layout (§5, lines 442-446), keyboard nav table (§4)
- `.planning/phases/09-ts-tui-json-rpc/09-CONTEXT.md` — D-29 deferred the live clock (reversed here by D-14); SessionPicker design lineage (Ctrl+S overlay)
- `.planning/phases/10-token-streaming/10-CONTEXT.md` — streaming/TUI store patterns that must not be broken by layout changes

</canonical_refs>

<code_context>
## Existing Code Insights

### Reusable Assets
- `RpcClient.sessions.*` methods (`rpc-client.ts:111-133`): list/switch/create/delete already implemented — `/session` and `/new` can call these directly
- `useAgentStore` Zustand store: `sessions`, `activeSessionId`, `conversation`, `resetConversation` — foundation for popup state and history display
- `SessionPicker` overlay pattern from 09 UI-SPEC (§3, §4): full-screen overlay + keyboard nav — reference for the new `/session` overlay
- `JSONLSessionStore.load()` (`session/store.py:60`) + `Session.to_events()` (`session/models.py:58`): message history source for the new history-loading RPC method
- InputBar `/sessions` branch (`app.tsx:39-42`): existing slash-command interception pattern to extend for `/session` and `/new`

### Established Patterns
- Slash commands intercepted in the TUI InputBar before calling `submitPrompt` (`app.tsx:36-48`)
- Keyboard-first interaction via Ink `useInput` with `isActive` gating per panel
- Store-based state (Zustand) with event handlers in `rpc-client.ts` mapping RPC notifications to store actions
- Fixed-width right panel concept already designed in 09 UI-SPEC (30-col StatsPanel)
- Async-first JSON-RPC: frontend never touches Python internals, only RPC methods

### Integration Points
- InputBar command handling: add `/session` and `/new` branches alongside existing `/sessions` (app.tsx)
- App.tsx layout: remove SessionPanel, add DatePanel on the right, keep Header/Conversation/ToolMonitor
- RPC client + backend adapter: add `sessions.get`-style method for history loading (adapter.py register_all, runtime/store)
- Store: new action to ingest loaded history into `conversation`; `setActiveSession` already exists
- Date panel reads from a 1-second ticker; session name from store `activeSessionId`

</code_context>

<specifics>
## Specific Ideas

- "Conversation screen and on the other panel I wanted date and time" — driving layout request
- "/session if I put it in prompt input it should open a small popup that shows me all sessions and if I click any one of them then it continues" — driving popup request (evolved to full-screen keyboard overlay during discussion)
- "If I hit /new it should start a fresh conversation" — immediate fresh start, no confirm
- 09 UI-SPEC already designed a Date/Time StatsPanel with a live clock ("Live clock updates every second", line 484) — this phase implements that deferred piece

</specifics>

<deferred>
## Deferred Ideas

- Create/delete/rename sessions inside the `/session` overlay — user chose switch-only for this phase (the `[n]/[d]/[r]` hints from the removed SessionPanel are not relocated)
- Mouse-driven session picker — Ink keyboard navigation chosen instead
- Token count per session in the popup — would require backend changes beyond this phase's scope
- Configurable right-panel width — fixed ~24-30 cols for now

</deferred>

---

*Phase: 11-session-popup-and-panel-layout*
*Context gathered: 2026-07-31*
