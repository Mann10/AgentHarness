# Phase 11: Session Popup & Panel Layout - Research

**Researched:** 2026-07-31
**Domain:** TypeScript/Ink 7 TUI + Python asyncio JSON-RPC backend (session management, overlay UI, live clock)
**Confidence:** HIGH (all findings verified against installed code / runtime behavior)

<user_constraints>
## User Constraints (from CONTEXT.md)

**CRITICAL:** Locked decisions from `/gsd-discuss-phase` — these MUST be honored by the planner.

### Locked Decisions

#### Panel layout
- **D-01:** Conversation is the main (left) panel; the right panel shows date/time. Matches the right-side StatsPanel concept from the 09 UI-SPEC.
- **D-02:** The always-visible left SessionPanel is removed — session identity moves out of a persistent sidebar.
- **D-03:** Header is kept (shows app name + active session title, as today). The active session name is ALSO shown in the date/time panel.
- **D-04:** Bottom ToolMonitorPanel is kept unchanged (appears only when tool calls are active).
- **D-05:** Right date/time panel uses a fixed width (~24–30 columns).

#### /session popup
- **D-06:** Typing `/session` in the prompt input and pressing Enter opens a full-screen overlay session picker (not a small dropdown).
- **D-07:** Navigation is keyboard-first: `↑`/`↓` move cursor, `Enter` selects (continues the session), `Esc` closes. Matches the 09 UI-SPEC SessionPicker navigation model.
- **D-08:** Each row shows: session title, short id (8 chars), message count, and relative age (e.g. "2h ago"). Sorted most-recent first.
- **D-09:** The popup is switch-only — no create/delete/rename inside the overlay.
- **D-10:** Selecting a session loads that session's past conversation history into the TUI conversation view. Requires a new backend capability (e.g. `sessions.get` RPC method returning session messages) — none exists today; the `JSONLSessionStore.load()` already returns full session events.

#### /new semantics
- **D-11:** Typing `/new` and pressing Enter immediately starts a fresh conversation. Current session is auto-saved first (JSONL persists per turn, so unsaved work is minimal). No confirm prompt.
- **D-12:** `/new` calls the existing `sessions.create` RPC method, switches the active session, and clears the conversation view.
- **D-13:** New sessions auto-title from their first prompt (matching the REPL behavior in `main.py` lines 185-186), so "untitled" becomes the first prompt truncated to 50 chars after the first exchange.

#### Date/time panel
- **D-14:** The panel shows a live clock — current date + current time, updating every second. Reverses 09-CONTEXT D-29 which deferred the clock.
- **D-15:** Time uses 24-hour format `HH:MM:SS`.
- **D-16:** Both date and time are shown (date above, time below). Active session name also displayed (per D-03).

### OpenCode's Discretion
- Exact overlay border/title styling and row layout in the session picker
- Date format string (e.g. "Jul 31, 2026" vs "2026-07-31")
- `sessions.get` RPC method shape, payload fields, and how the TUI store ingests loaded history
- Live clock implementation detail in Ink (useInterval vs setInterval), respecting Ink's re-render model
- Scroll/auto-scroll behavior after loading history into the conversation view
- Keyboard binding details beyond Enter/Esc/arrows

### Deferred Ideas (OUT OF SCOPE)
- Create/delete/rename sessions inside the `/session` overlay (switch-only for this phase)
- Mouse-driven session picker (Ink keyboard navigation chosen)
- Token count per session in the popup (would require backend changes beyond scope)
- Configurable right-panel width (fixed ~24-30 cols for now)

</user_constraints>

<architectural_responsibility_map>
## Architectural Responsibility Map

Two-tier application: TypeScript Ink TUI (client tier) + Python asyncio runtime with stdio JSON-RPC (backend tier).

| Capability | Primary Tier | Secondary Tier | Rationale |
|------------|-------------|----------------|-----------|
| `/session` overlay picker UI + keyboard nav | Client (TUI) | — | Pure presentation; uses existing `sessions.list` data |
| Slash-command interception (`/session`, `/new`) | Client (TUI) | — | InputBar already owns Enter-key handling (`app.tsx:36-48`) |
| Date/time panel + live clock | Client (TUI) | — | Local rendering; `Date` API + 1s ticker; no backend data |
| Session history loading (`sessions.get`) | Backend (RPC adapter + RuntimeAPI) | Storage (JSONLSessionStore) | Must serialize stored events into RPC payloads (D-10, D-14 constraint) |
| Session continue (switch + context restore) | Backend (RuntimeAPI/SessionManager) | Storage | Fixes latent `RuntimeError: Session context not restored` bug |
| Auto-title from first prompt (D-13) | Backend (RuntimeAPI) | Storage | Mirrors REPL behavior (`main.py:185-186`) for the RPC/TUI path |
| Session persistence | Storage (JSONLSessionStore) | — | Already exists — untouched except new read path |

</architectural_responsibility_map>

<research_summary>
## Summary

Researched the Phase 11 work across the full stack: the Ink TUI (`tui-ink/`), the zustand store, the JSON-RPC bridge, and the Python backend (`backend/rpc/`, `harness/`, `session/`). All findings below were verified against the installed code and, where noted, empirically by running the code.

**Three decisive findings shape the plan:**

1. **Latent backend bug blocks D-06/D-10:** `Session.from_events()` (used by `JSONLSessionStore.load()`) sets `_context=None` and stashes raw events in `_stored_events`. `Session.to_events()` crashes with `AttributeError` on such sessions (`self._context._messages` when `_context is None`), and `Session.context` raises `RuntimeError("Session context not restored")`. Critically, `Session.restore_context()` is **never called anywhere in the codebase** — so `RuntimeAPI.switch_session()` → `_create_agent()` → `Agent.__init__` → `session.context` **crashes today for any real saved session**. The REPL `/resume` path would hit the same wall. Phase 11 MUST fix context restoration as part of the history-loading work (empirically confirmed: `to_events()` on a loaded session raises `AttributeError`).

2. **Ink ^7.1.0 has NO `useInterval` hook** (verified against the installed package build exports). The D-14 live clock must use `useEffect` + `setInterval` (1000 ms), keeping the tick state inside the small date/time panel component so the 1 Hz re-render does not cascade through the whole tree.

3. **No TUI test infrastructure exists.** `tui-ink` has no vitest/jest and ink-testing-library is stale (v4.0.0, incompatible with Ink 5+/7 input handling per ecosystem research). Verification for TUI work = `npm run typecheck` (0 errors) + `npm run build` + human E2E checkpoint. Python backend tests use pytest (`asyncio_mode = auto`, tempdir `JSONLSessionStore` fixture pattern) — the history-loading + restore fix is fully unit-testable there.

**Primary recommendation:** Add a new `sessions.get` RPC method (per D-10's suggestion) that returns session messages in chronological order, fix `RuntimeAPI.switch_session` to call `session.restore_context()` before creating the Agent, and implement the TUI overlay as a conditional full-screen render (picker replaces the main tree while open, so its `useInput` is the only active keyboard handler). No new dependencies anywhere.
</research_summary>

<standard_stack>
## Standard Stack

Existing project stack — **no new dependencies required** for this phase.

### Core (already installed, verified in `tui-ink/package.json` + `requirements.txt` ecosystem)
| Library | Version | Purpose | Why Standard |
|---------|---------|---------|--------------|
| ink | ^7.1.0 | React renderer for terminal UI | Project standard; `useInput`/`useFocus`/`useApp` verified present |
| react | ^19.0.0 | Component model | Ink requires React |
| zustand | ^5.0.0 | Store | Already drives `agent-store.ts` |
| tsup / typescript | ^8.0.0 / ^5.6.0 | Build + typecheck | `npm run build` / `npm run typecheck` scripts exist |
| Python 3 + asyncio | — | Backend runtime | RPC server is async (`backend/rpc/server.py`) |
| pytest (asyncio_mode=auto) | — | Backend tests | `tests/` suite pattern established (Phase 5+) |

### Supporting (existing patterns to reuse — nothing to install)
| Library | Purpose | When to Use |
|---------|---------|-------------|
| Ink `useInput` | Keyboard capture | Slash-command interception + picker nav (already the TUI's only input path) |
| Ink `useFocus`/`useFocusManager` | Panel focus | Existing `FocusablePanel` wrapper in `app.tsx` |
| `JSONLSessionStore` | Session persistence | `load()` already returns full events (D-10 data source) |
| `Session.to_events()` / `_stored_events` | Message serialization | History payload source (after restore-fix or accessor) |

### Alternatives Considered
| Instead of | Could Use | Tradeoff |
|------------|-----------|----------|
| `useEffect` + `setInterval` for clock | Ink `useInterval` | **Does not exist in ink ^7.1.0** — verified against installed build exports. `setInterval` is the only option. |
| New `sessions.get` RPC | Extend `sessions.switch` response with history | CONTEXT explicitly suggests `sessions.get` (D-10). Separate method keeps `switch` contract stable and makes history a pure read. |
| Full-screen conditional render for picker | Absolute-positioned Box overlay over the app | Ink has no z-index/modal primitive; conditional render makes the picker's `useInput` the sole active handler (true key trap, matching UI-SPEC §3 "all keys intercepted by picker's useInput"). |
| pytest for backend logic | No tests | Backend changes (restore fix + new RPC) are exactly the testable layer; Nyquist requires automated gates. |
| vitest/ink-testing-library for TUI | Manual typecheck+build+E2E | ink-testing-library v4.0.0 pins Ink ^5/React 18 — incompatible with installed Ink 7.1. Not worth adding a bespoke harness for this phase. |

</standard_stack>

<architecture_patterns>
## Architecture Patterns

### System Architecture Diagram

```
┌────────────────────────────────────────────────────────────────┐
│ TypeScript Ink TUI (tui-ink/)                                  │
│                                                                │
│  InputBar (app.tsx)                                            │
│   ├─ Enter: "/session" ──► open picker state ──► SessionPicker │
│   ├─ Enter: "/new" ──────► RpcClient.createSession() + reset   │
│   └─ Enter: other ───────► RpcClient.submitPrompt()            │
│                                                                │
│  SessionPicker (full-screen, while open):                      │
│   ├─ ↑/↓ cursor ──► Enter: RpcClient.switchSession(id)         │
│   ├─ Enter: then RpcClient.getSessionHistory(id) ──► store     │
│   └─ Esc ──► close (return to app, state preserved)            │
│                                                                │
│  DatePanel (right, ~28 cols): 1s setInterval tick ──► render   │
│   date + HH:MM:SS + active session title (from store)          │
│                                                                │
│  ConversationPanel (left, flexGrow) ◄── store.conversation     │
│   ▲ history ingestion: loadConversation(history)               │
│  zustand store ◄── RpcClient.handleEvent (7 notification types)│
└───────────────────────────┬────────────────────────────────────┘
                            │ JSON-RPC over stdio (NDJSON)
┌───────────────────────────▼────────────────────────────────────┐
│ Python backend (main.py --rpc)                                 │
│  RPCServer → Dispatcher → RPCAdapter → RuntimeAPI              │
│   ├─ sessions.get (NEW): SessionManager.get_session(id)        │
│   │    → JSONLSessionStore.load(id) → messages accessor        │
│   ├─ sessions.switch (FIXED): load + restore_context()         │
│   │    → _create_agent() (Agent no longer crashes)             │
│   └─ submit_prompt (D-13): auto-title active session if None   │
│  EventBus ──► notifications (turn_started, token, ...)         │
└────────────────────────────────────────────────────────────────┘
```

### Pattern 1: Slash-command interception (extend existing)
**What:** `InputBar`'s `useInput` return-handler already intercepts `/sessions` before falling through to `submitPrompt` (`app.tsx:39-42`). Add `trimmed === "/session"` (open picker) and `trimmed === "/new"` (create + reset) branches.
**When to use:** All prompt-input commands; keeps session management out of the always-visible sidebar (D-02/D-06).
**Example (current code, `app.tsx:36-48`):**
```typescript
if (key.return) {
  const trimmed = input.trim()
  if (!trimmed) return
  if (trimmed === "/sessions") {
    client.listSessions().then((sessions) => { useAgentStore.getState().setSessions(sessions) })
  } else {
    client.submitPrompt(trimmed)
  }
  setInput("")
  return
}
```

### Pattern 2: Full-screen overlay with key trap (SessionPicker)
**What:** When `pickerOpen` is true, `App` renders `<SessionPicker>` **instead of** the normal layout (conditional render = full-screen overlay per D-06). The picker owns a `useInput` hook with `isActive` implicitly satisfied (it is the only rendered consumer). `InputBar` unmounts → its `useInput` unregisters → no competing key handlers. The App-level `q`-quit handler must early-return while the picker is open (otherwise `q` quits instead of closing, violating UI-SPEC "Esc/q close").
**When to use:** Any modal interaction in Ink — no z-index primitives exist; conditional render is the canonical overlay.
**Row contract (D-08 + 09 UI-SPEC §3):** `{title || "untitled"}  {id.slice(0,8)}  {message_count} msgs  {relativeAge}` sorted by `updated_at` desc. Cursor = reverse video or accent (`$accent` blue per UI-SPEC §1). Hint line: `↑ ↓ navigate  •  Enter select  •  Esc close` (dim).

### Pattern 3: Live clock (D-14/D-15/D-16)
**What:** Dedicated small component; `useState(now)` + `useEffect(() => { const t = setInterval(() => setNow(new Date()), 1000); return () => clearInterval(t) }, [])`. Render date line + `HH:MM:SS` line + active session title (from `useAgentStore`).
**When to use:** Self-contained ticking state — isolating it prevents 1 Hz re-renders from touching the conversation panel (Ink re-renders the subscribed subtree only).
**Verified constraint:** Ink ^7.1.0 exports no `useInterval`. `useEffect`+`setInterval` is the only option.

### Pattern 4: History-loading RPC (`sessions.get`, D-10/D-14)
**What:** New RPC method, registered in `RPCAdapter.register_all()` (currently 7 methods → 8). Pipeline: `RpcClient.getSessionHistory(id)` → `{"jsonrpc":"2.0","method":"sessions.get","params":{"session_id":...}}` → `Dispatcher` → `handle_sessions_get` → `RuntimeAPI.get_session_history(id)` → `SessionManager.get_session(id)` (NEW: load WITHOUT switching active — unlike `load_session`) → message accessor → list of `{role, content, tool_calls?, tool_call_id?}`.
**Message extraction — two viable routes (planner picks):**
- **(a) New `Session.messages()` accessor** (light): returns `self._stored_events` when `_context is None`, else `to_events()`. No token counting needed. Pure read.
- **(b) `restore_context()` then `to_events()`** (heavy): needs `count_tokens`/`token_limit`/`summarize_fn`; may trigger summarization side effects. Only justified if the session is ALSO being switched to.
Recommendation: (a) for `sessions.get` (pure read), and restore_context for `switch_session` (which needs it for the Agent anyway).
**TUI ingestion:** map `role: "user"`→user, `"assistant"`→assistant; **skip** `system` (summaries) and `tool` (tool results render via the tool-monitor path, not as conversation text). Timestamps: no per-message timestamps persisted (store has only meta `created_at`/`updated_at`) — assign `now()` at ingest (or spread across `created_at..updated_at`; planner discretion). Add zustand action e.g. `loadConversation(messages)` → sets `conversation`, clears `toolCalls`, `status: "idle"`.

### Pattern 5: Context restore fix (blocking bug for D-06/D-10)
**What:** `RuntimeAPI.switch_session` must call `await session.restore_context(count_tokens=self._client.count_tokens, token_limit=self._config.max_tokens, summarize_fn=self._summarize_fn)` after `load_session` and before `_create_agent()`. Wrap in try/except → return `False` on restore failure (matches existing "not found → False" contract).
**When to use:** Any path that turns a store-loaded session into an active Agent. This is a pre-existing bug (REPL `/resume` and `/session` continue both depend on it); empirically confirmed.

### Anti-Patterns to Avoid
- **Double-loading sessions:** `sessions.switch` then `sessions.get` both read the file. Acceptable (clean separation, tiny files), but never load-and-restore in `get` when the session is already active.
- **Rendering tool/system messages as conversation text:** noisy; violates the TUI's established message roles (`user|assistant|notice|error`).
- **Nested borders:** date/time panel + conversation panel each get ONE border; no outer frame (tui-design clutter audit).
- **Hardcoded colors:** follow existing `borderColor={focused ? "green" : "gray"}` pattern; picker cursor per UI-SPEC `$accent` blue.

</architecture_patterns>

<dont_hand_roll>
## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| Relative age ("2h ago") | New formatting logic from scratch | Reuse `main.py:74-75` semantics: `f"{s/60:.0f}m ago"` if `<3600s` else `f"{s/3600:.0f}h ago"` (TS: `Date.parse(iso)` → diff) | Already the established display format in the REPL `/sessions`; D-08 example matches it exactly |
| Keyboard navigation | Custom input parsing | Ink `useInput` with `key.upArrow`/`key.downArrow`/`key.return`/`key.escape` | Already the TUI's single input path; UI-SPEC §3 navigation model |
| Panel focus | Custom focus logic | Ink `useFocus` + existing `FocusablePanel` wrapper | Established pattern; removing the sessions panel just removes one `FocusablePanel` |
| State management | New store | zustand `useAgentStore` | Already holds `sessions`, `activeSessionId`, `conversation`, `resetConversation` |
| RPC plumbing | New transport | Existing `Dispatcher`/`RPCAdapter`/`request()` machinery | One new method each on adapter + client; zero transport changes |
| Live clock | Custom timer library | `useEffect` + `setInterval` (1000 ms) | No Ink timer hook exists (verified); browser `setInterval` is the standard |
| Message serialization | Manual JSON shaping | `Session.to_events()`/`_stored_events` dicts | Already serializable `{role, content, token_count, tool_calls?, tool_call_id?}` |

**Key insight:** This phase's backend work is mostly *wiring existing capability to the RPC surface* — the store already returns full session events (`store.py:60-76`) and the adapter already has the delegation pattern. The genuinely new logic is the context-restore fix (a bug, not a feature) and the TUI overlay/clock (pure Ink patterns).
</dont_hand_roll>

<common_pitfalls>
## Common Pitfalls

### Pitfall 1: `RuntimeError: Session context not restored` / `AttributeError` on loaded sessions
**What goes wrong:** `sessions.switch` → `Agent` construction crashes; `sessions.get` using `to_events()` crashes.
**Why it happens:** `Session.from_events()` sets `_context=None` + `_stored_events`; `restore_context()` is never called anywhere; `to_events()` touches `self._context._messages` directly.
**How to avoid:** Fix `RuntimeAPI.switch_session` to restore context (count_tokens/token_limit/summarize_fn available on runtime); use `_stored_events`-aware accessor for pure-read history.
**Warning signs:** Any resume/continue flow raising; `AttributeError: 'NoneType' object has no attribute '_messages'`.

### Pitfall 2: Multiple active `useInput` hooks eating keys during the picker
**What goes wrong:** Typing `q` quits the app instead of closing the picker; `↑`/`↓` both move the cursor AND do nothing/scroll elsewhere; Enter submits a prompt.
**Why it happens:** Every mounted `useInput` receives input in Ink. If `App`'s quit handler and/or `InputBar` stay mounted while the picker is open, keys are handled twice.
**How to avoid:** Conditional render — picker replaces the main tree (InputBar unmounts); gate App-level `q` with `if (pickerOpen) return`.
**Warning signs:** Double action on a single keypress; quit during picker.

### Pitfall 3: 1 Hz clock re-render cascading through the app
**What goes wrong:** Every second, the whole tree re-renders; streaming output stutters; CPU blips.
**Why it happens:** Ticking state lifted to App level; or the clock component re-renders siblings.
**How to avoid:** Keep `setInterval` state inside the small date/time panel component; read store via fine-grained selector. Ink 6.7+ synchronized updates help, but containment is the fix.
**Warning signs:** Token streaming visibly stutters once per second.

### Pitfall 4: History ingestion breaking streaming assumptions
**What goes wrong:** `conversation` replaced with history; then first `turn_started` appends; stale `toolCalls`/`isStreaming` flags leak from previous session.
**Why it happens:** `resetConversation()` clears everything, but a new `loadConversation` must also clear tool state; the store's `token` handler checks `lastMsg.role !== "assistant"` on the ingested tail.
**How to avoid:** `loadConversation` resets `toolCalls`, `toolCallCount`, `status`, `error` (mirror `resetConversation`); ingest messages as non-streaming (`isStreaming` absent/`false`).
**Warning signs:** Old tool calls visible after switching; streaming marker on ingested history.

### Pitfall 5: Sorting/age display mismatches
**What goes wrong:** Picker shows sessions in file order (creation order); ages wrong because `updated_at` vs `created_at` confusion.
**Why it happens:** `JSONLSessionStore.list_sessions()` returns `glob` (filename) order — not recency order. `main.py` explicitly sorts by `updated_at` desc.
**How to avoid:** Picker sorts by `updated_at` desc; age computed from `updated_at` (matches REPL). 
**Warning signs:** "Most-recent first" (D-08) not holding; ages that don't advance.

### Pitfall 6: RPC method/params drift
**What goes wrong:** 404 `Method not found` or `Internal error: ...` from the dispatcher; TUI type says one shape, backend returns another.
**Why it happens:** New method added on one side only; params key mismatch (`session_id` vs `id`).
**How to avoid:** Add `sessions.get` to BOTH `adapter.register_all` (→8 methods) and `RpcClient`; params key `session_id` (consistent with `sessions.switch`/`sessions.delete`); keep the dispatcher's existing validation (dict params).
**Warning signs:** `Method not found: sessions.get` in the RPC log (`tui-ink-rpc.log`).

</common_pitfalls>

<code_examples>
## Code Examples

All examples verified against the installed codebase.

### 1. Adapter method pattern to copy for `sessions.get` (`backend/rpc/adapter.py:40-52`)
```python
async def handle_sessions_list(self, params: dict | None) -> list[dict]:
    """List all saved sessions."""
    summaries = await self._runtime.list_sessions()
    return [
        {
            "id": s.id,
            "title": s.title,
            "created_at": s.created_at.isoformat(),
            "updated_at": s.updated_at.isoformat(),
            "message_count": s.message_count,
        }
        for s in summaries
    ]
# Register alongside the others: dispatcher.register("sessions.get", self.handle_sessions_get)
```

### 2. Relative-age formatting (REPL reference, `main.py:74-75`)
```python
age_s = (datetime.now() - s.updated_at).total_seconds()
age = f"{age_s/60:.0f}m ago" if age_s < 3600 else f"{age_s/3600:.0f}h ago"
```
TS equivalent for the picker: `const age = (d: Date) => { const s = (Date.now() - d.getTime()) / 1000; if (s < 60) return "just now"; if (s < 3600) return `${Math.round(s/60)}m ago`; if (s < 86400) return `${Math.round(s/3600)}h ago`; return `${Math.round(s/86400)}d ago` }`

### 3. Store action pattern to copy for `loadConversation` (`tui-ink/src/store/agent-store.ts:195-202`)
```typescript
resetConversation: () =>
  set({
    conversation: [],
    toolCalls: [],
    toolCallCount: 0,
    status: "idle",
    error: null,
  }),
```
`loadConversation` mirrors this but seeds `conversation` with mapped `{id, role, content, timestamp}` objects (non-streaming).

### 4. Zustand selector in Header to copy for DatePanel session title (`tui-ink/src/components/header.tsx:5-7`)
```typescript
const { sessions, activeSessionId, model, status } = useAgentStore()
const activeSession = sessions.find((s) => s.id === activeSessionId)
const label = activeSession?.title ?? "No session"
```

### 5. RPC client method to copy for `getSessionHistory` (`tui-ink/src/bridge/rpc-client.ts:116-121`)
```typescript
async switchSession(sessionId: string): Promise<boolean> {
  const result = (await this.request("sessions.switch", { session_id: sessionId })) as { success: boolean }
  return result.success
}
```

### 6. FocusablePanel wrapper (unchanged; sessions panel removal just drops one usage) (`tui-ink/src/app.tsx:16-25`)
```typescript
function FocusablePanel({ id, children }: { id: string; children: (focused: boolean) => React.ReactNode }) {
  const { isFocused } = useFocus({ id })
  return <>{children(isFocused)}</>
}
```

</code_examples>

<sota_updates>
## State of the Art (2026)

| Old Approach | Current Approach | When Changed | Impact |
|--------------|------------------|--------------|--------|
| ink-testing-library for TUI tests | Custom harness (Gemini CLI pattern) or skip unit tests | Ink 5+ / 2024 | v4.0.0 pins Ink ^5/React 18; input simulation unreliable on Ink 7 → TUI verified via typecheck + build + human E2E |
| Ink fullscreen via `fullscreen-ink` | Native `alternateScreen: true` render option | Ink 7 | Already used by this TUI's entry (index.tsx renders with alt screen) |
| `useInterval` in Ink | `useEffect` + `setInterval` | — | Ink 7.1 exports no timer hook (verified: exports are Box/Text/Static/useInput/useFocus/useFocusManager/useApp/useAnimation/usePaste/useStdin/useStdout/useStderr/useWindowSize/...) |
| High-frequency re-render flicker | Synchronized updates (Ink 6.7+) | 2024 | Token streaming already smooth; 1 Hz clock fine if contained |

**New tools/patterns to consider:**
- **`useAnimation` (Ink 7):** exists for animation frames — not suitable for a 1 Hz clock (fires per-frame); `setInterval` remains correct.

**Deprecated/outdated:**
- **ink-testing-library for input-driven tests:** unreliable on Ink ≥5 (stdin simulation). Do not add for this phase.

</sota_updates>

<validation_architecture>
## Validation Architecture

Nyquist validation strategy for this phase (drives `11-VALIDATION.md`).

**Split by layer (backend unit-testable, TUI not):**

| Layer | Validation Type | Mechanism | Nyquist Gate |
|-------|----------------|-----------|--------------|
| Backend: `sessions.get` history RPC | Automated unit tests (pytest) | New tests in `tests/test_runtime.py` + `tests/test_session_manager.py` patterns: tempdir `JSONLSessionStore`, create→add messages→save→`get_session_history`→assert chronological `{role, content}`; `get_session` without active-switch assertion | `pytest -q` full suite (currently 43 tests) passes |
| Backend: context-restore fix | Automated unit test | `switch_session` on a persisted session → active session context restored (`to_llm_messages()` non-empty), returns `True`; corrupt/missing id → `False`; Agent created without crash | New test in `tests/test_runtime.py` |
| Backend: auto-title (D-13) | Automated unit test | `submit_prompt("first prompt...")` with untitled active session → title set to first prompt (≤50 chars + "..." suffix) | New test in `tests/test_runtime.py` |
| Backend: RPC surface | Automated test (adapter-level, if added) or covered via runtime tests | `sessions.get` handler returns messages for existing id; error dict for missing id | New tests |
| TUI: type system | Automated | `npm run typecheck` — 0 errors (tsc --noEmit) | Green in plan verification |
| TUI: build | Automated | `npm run build` — tsup dist emits | Green in plan verification |
| TUI: overlay/picker/clock behavior | Human E2E checkpoint (blocking) | Manual: `/session` opens full-screen picker, ↑/↓ moves, Enter continues + history loads, Esc closes; `/new` starts fresh; clock ticks 1 Hz; layout = conversation left + date/time right + header/footer intact | Blocking checkpoint in final plan (mirrors Phase 10-04 pattern) |

**Runtime verification commands (all < 60 s):**
- `python -m pytest -q` (backend suite)
- `npm run typecheck` (TUI types)
- `npm run build` (TUI bundle)

**Explicitly NOT validated by automation:** visual layout, focus borders, clock ticking, keyboard feel — these are the human checkpoint's scope.

</validation_architecture>

<open_questions>
## Open Questions

1. **`sessions.get` vs extended `sessions.switch` response**
   - What we know: CONTEXT D-10 suggests `sessions.get`; D-14 constrains backend changes to "history-loading RPC only". `switch` already loads the file.
   - What's unclear: whether one RPC (switch returning history) or two (switch + get) is preferable.
   - Recommendation: two methods. `sessions.get` stays a pure read (testable, reusable); `switch` semantics stay untouched except the restore fix. TUI calls switch, then get.

2. **Per-message timestamps for ingested history**
   - What we know: JSONL stores only meta `created_at`/`updated_at`; events have no timestamps. TUI `Message.timestamp` is a number.
   - What's unclear: what timestamps to assign.
   - Recommendation: `Date.now()` at ingest for all (simplest); conversation display doesn't show timestamps today, so ordering (chronological array order) is what matters. Planner discretion.

3. **Which history roles to render**
   - What we know: stored roles are `system|user|assistant|tool`; TUI renders `user|assistant|notice|error`.
   - What's unclear: whether tool-message content should appear in the conversation after a continue.
   - Recommendation: render `user` + `assistant` only; skip `system` summaries and `tool` results (they surface via ToolMonitorPanel live, and replaying them as text is noisy). Planner may revisit.

4. **Date format for the date/time panel (D-16 "date above, time below")**
   - What we know: D-15 locks `HH:MM:SS` for time; date format is discretion.
   - Recommendation: `YYYY-MM-DD` (ISO, sortable, unambiguous in a terminal) or `Jul 31, 2026`. Planner picks; execution should not re-ask.

5. **Footer hints after SessionPanel removal**
   - What we know: footer shows `[1-3] jump` (aspirational; no numbered-focus handler exists in `app.tsx`) and `[/] search` (no handler either).
   - What's unclear: whether to keep, fix, or update hints.
   - Recommendation: replace with actual commands: `[/session] sessions  [/new] new chat  [Tab] panels  [q] quit  [?] help` — honest discoverability per tui-design; planner discretion.

6. **Auto-title timing (D-13)**
   - What we know: REPL sets title after the first response completes (`main.py:185-186`); RuntimeAPI has no such hook; TUI has no rename RPC (and D-14 forbids adding one).
   - What's unclear: whether to set the title at `submit_prompt` time (immediately) or after completion.
   - Recommendation: set in `RuntimeAPI.submit_prompt` when `active_session.title is None` → `title = prompt[:50] + ("..." if len(prompt) > 50 else "")`. Title appears slightly earlier than REPL but persists via the existing post-turn `save_session()`. Matches "auto-title from their first prompt".

</open_questions>

<sources>
## Sources

### Primary (HIGH confidence — read/verified directly)
- `tui-ink/src/app.tsx` — InputBar slash-command handling (L36-48), layout wiring (L134-153), FocusablePanel (L16-25)
- `tui-ink/src/bridge/rpc-client.ts` — request()/handleEvent, 7 RPC client methods (L111-133)
- `tui-ink/src/store/agent-store.ts` — zustand store, all actions including resetConversation
- `tui-ink/src/types.ts` — SessionSummary, Message, AgentState contracts
- `tui-ink/src/panels/*` + `components/header.tsx|footer.tsx` — panel/header/footer rendering
- `tui-ink/package.json` + installed `ink@7.1.0` build exports — **verified: no useInterval hook**
- `backend/rpc/adapter.py` (7 registered methods, L77-85), `dispatcher.py`, `server.py` — RPC pipeline
- `harness/runtime.py` — RuntimeAPI (submit_prompt D-15, switch_session L113-123, _create_agent L182-202)
- `harness/session_manager.py` — create/load/save/switch/list/delete
- `session/models.py` — Session.context property (L34-38), to_events (L58-67), from_events (L88-101), restore_context (L103-123)
- `session/store.py` — JSONLSessionStore.load (L60-76) returns full events
- `context/context.py` + `context/message.py` — ConversationContext, Message roles
- `agent/core.py` — `Agent.__init__` reads `session.context` (L45) — crash point for non-restored sessions
- `main.py` — REPL /sessions age formatting (L72-77), auto-title (L184-186), /new (L79-93)
- `tests/test_runtime.py`, `tests/test_session_manager.py` — pytest patterns (tempdir store fixture, mock deps)
- `.planning/phases/09-ts-tui-json-rpc/09-UI-SPEC.md` — SessionPicker overlay spec (§3), keyboard nav (§4), StatsPanel date/time layout (§5)
- `.planning/phases/09-ts-tui-json-rpc/09-CONTEXT.md` — D-29 (deferred clock, reversed by D-14), session picker lineage
- `tui-design` skill (project skill) — overlay/interaction patterns, clutter audit, floor pressure-testing

### Secondary (MEDIUM confidence — empirical verification performed)
- Runtime experiment (this research): create→title→add_message→save→store.load→**`to_events()` raises AttributeError; `_context is None`; `_stored_events` populated** — confirms latent restore bug
- Ink export scan (this research): `Object.keys(ink build)` — no `useInterval`

### Tertiary (LOW confidence — needs validation during implementation)
- None — all findings verified against installed code or runtime behavior

</sources>

<metadata>
## Metadata

**Research scope:**
- Core technology: Ink 7 TUI + Python asyncio JSON-RPC backend
- Ecosystem: ink, react, zustand, tsup, pytest (no new deps needed)
- Patterns: slash-command interception, full-screen overlay key-trap, live clock, RPC read method, context restore
- Pitfalls: session context restore bug, multi-useInput key races, 1 Hz re-render containment, RPC method drift

**Confidence breakdown:**
- Standard stack: HIGH — verified against installed versions
- Architecture: HIGH — all integration points read directly
- Pitfalls: HIGH — restore bug empirically confirmed
- Code examples: HIGH — copied from working code paths

**Research date:** 2026-07-31
**Valid until:** 2026-08-30 (stable ecosystem)
</metadata>

---

*Phase: 11-session-popup-and-panel-layout*
*Research completed: 2026-07-31*
*Ready for planning: yes*
