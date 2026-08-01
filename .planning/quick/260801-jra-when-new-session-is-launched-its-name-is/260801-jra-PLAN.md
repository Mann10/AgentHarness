---
phase: 260801-jra-when-new-session-is-launched-its-name-is
plan: 01
type: execute
wave: 1
depends_on: []
files_modified: [harness/runtime.py, tests/test_runtime.py, tui-ink/src/app.tsx]
autonomous: false
requirements: [D-11, D-12, D-13]
user_setup: []

must_haves:
  truths:
    - "After /new, the new session appears in the store's sessions array, so the conversation panel shows 'untitled' (not a stale previous name)"
    - "As soon as the user submits the first question, the conversation panel header shows the auto-title — first line of the prompt, truncated to 15 chars + '...' — without switching sessions"
    - "The auto-title is on disk by the time the chat RPC resolves, so an immediate sessions.list read returns the title, not None"
  artifacts:
    - path: "harness/runtime.py"
      provides: "Synchronous auto-title persistence inside submit_prompt"
      contains: "save_session"
    - path: "tests/test_runtime.py"
      provides: "Immediate-persistence regression test (no sleep before list_sessions)"
      contains: "test_submit_prompt_title_persists_to_store"
    - path: "tui-ink/src/app.tsx"
      provides: "Sessions refresh after /new and after each submitPrompt"
      contains: "submitPrompt(trimmed).then"
  key_links:
    - from: "harness/runtime.py"
      to: "harness/session_manager.py"
      via: "await self._session_manager.save_session() in submit_prompt, after session.title = derive_title(prompt) and before scheduler dispatch"
      pattern: "save_session\\(\\)"
    - from: "tui-ink/src/app.tsx"
      to: "tui-ink/src/bridge/rpc-client.ts"
      via: "submitPrompt(trimmed) resolves -> refreshSessions() -> client.listSessions() -> setSessions"
      pattern: "submitPrompt\\(trimmed\\)\\.then"
---

<objective>
Fix the stale session-name bug: a new session's auto-title never appears in the conversation panel until the user switches sessions.

Purpose: The root cause is two-sided — (a) `submit_prompt` sets the auto-title in-memory but does NOT persist it until `on_turn_complete` fires (per-turn save), so `store.list_sessions()` (a disk read) still returns `title=None` when called right after the chat RPC resolves; and (b) the TUI never refreshes its `sessions` array after `/new` or after a prompt submit, so the ConversationPanel/Header/DatePanel keep reading a stale array that lacks the new session / its title. Fix (a) on the backend (persist the title synchronously in `submit_prompt`) and (b) in the TUI (refresh sessions after `/new` and after each submit). The existing truncation logic (`derive_title`, first line, ≤15 chars + "...") is unchanged — per D-13, the title arrives pre-truncated from the backend.

Output: `harness/runtime.py` persists auto-titles immediately; `tui-ink/src/app.tsx` refreshes sessions so panel titles update on first question; regression test; human E2E verified.
</objective>

<execution_context>
@./.opencode/get-shit-done/workflows/execute-plan.md
@./.opencode/get-shit-done/templates/summary.md
</execution_context>

<context>
@.planning/STATE.md
@.planning/phases/11-session-popup-and-panel-layout/11-CONTEXT.md

# Root cause (empirically confirmed 2026-08-01)
- `harness/runtime.py` L82-86 sets `session.title = derive_title(prompt)` in-memory; persistence only happens later via Scheduler's `on_turn_complete` callback (`runtime.start()` L188 wires `save_session`). Confirmed with a probe: `list_sessions()` called immediately after `submit_prompt` returns reads `title=None` from disk.
- `backend/rpc/adapter.py` `handle_chat` awaits `submit_prompt` then returns `{"status": "accepted"}` — so by the time the TUI's chat RPC resolves, the in-memory title is set but not persisted.
- `tui-ink/src/app.tsx` `/new` branch (L44-48) calls `client.createSession()` + `setActiveSession(id)` + `resetConversation()` but never refreshes `sessions`; the submit branch (L54) `client.submitPrompt(trimmed)` is fire-and-forget with no refresh.
- `tui-ink/src/panels/conversation-panel.tsx` L13-14: `sessions.find((s) => s.id === activeSessionId)?.title ?? "untitled"` — stale array = fallback title.
- Verified fix behavior empirically: with `await rt._session_manager.save_session()` inserted in `submit_prompt`, an immediate `list_sessions()` returns `"a persistent ti..."`; a second submit does NOT clobber the title (the `if session.title is None` guard holds).

<interfaces>
<!-- Verified against installed code. Executor must NOT re-explore. -->

From harness/runtime.py (submit_prompt, L65-86 — exact current shape):
```python
async def submit_prompt(self, prompt: str) -> None:
    """Submit a prompt for execution. Returns immediately (D-15)."""
    if self._scheduler is None:
        logger.warning("Runtime not started, ignoring prompt")
        return
    if self._session_manager.active_session is None:
        await self._session_manager.create_session(
            system_prompt=self._config.system_prompt,
            count_tokens=self._client.count_tokens,
            token_limit=self._config.max_tokens,
            summarize_fn=self._summarize_fn,
        )
        await self._create_agent()
    # D-13: auto-title new sessions from their first prompt (REPL parity)
    session = self._session_manager.active_session
    if session is not None and session.title is None:
        session.title = derive_title(prompt)
    await self._scheduler.submit_prompt(prompt)
```

From harness/session_manager.py:
```python
async def save_session(self) -> None:
    """Persist the active session if one exists. Idempotent if no active session."""
    if self._active_session is not None:
        self._active_session.updated_at = datetime.now()
        await self._store.save(self._active_session)
        logger.debug("Saved session %s", self._active_session.id[:8])
```
`store.save` (session/store.py L42-73) rewrites the meta line in place when `title` changed (meta_changed path) — safe when called before the turn adds messages; the later `on_turn_complete` save appends only `unpersisted_events()`. All saves are awaited sequentially on the event loop (no threads) — no concurrent file access.

From tui-ink/src/bridge/rpc-client.ts:
```typescript
async submitPrompt(prompt: string): Promise<void>     // resolves with chat RPC response {"status":"accepted"}
async listSessions(): Promise<SessionSummary[]>        // sessions.list -> SessionSummary[] { id, title: string|null, created_at, updated_at, message_count }
```
The chat RPC response is sent AFTER `submit_prompt` has fully run on the backend (adapter awaits it), so a `listSessions()` issued in the `.then()` after `submitPrompt` resolves is guaranteed to see the persisted title once task 1 lands.

From tui-ink/src/store/agent-store.ts:
```typescript
setSessions: (sessions: SessionSummary[]) => void     // replaces the sessions array; ConversationPanel/Header/DatePanel re-render from it
```

From tui-ink/src/app.tsx InputBar (L28-81, exact current shape — the three branches to touch):
```typescript
} else if (trimmed === "/new") {
  // D-11/D-12: immediate fresh start — create, switch active, clear view. No confirm.
  client.createSession().then((id) => {
    const store = useAgentStore.getState()
    store.setActiveSession(id)
    store.resetConversation()
  })
} else if (trimmed === "/sessions") {
  client.listSessions().then((sessions) => {
    useAgentStore.getState().setSessions(sessions)
  })
} else {
  client.submitPrompt(trimmed)
}
```

Title truncation: `derive_title` (session/models.py L17-26) — first line, `TITLE_MAX_CHARS = 15`, `"..."` suffix when longer. UNCHANGED by this plan (D-13: use existing logic; do not re-truncate in the TUI).
</interfaces>

<tasks>

<task type="auto" tdd="true">
  <name>task 01-1: persist auto-title synchronously in submit_prompt</name>
  <files>harness/runtime.py, tests/test_runtime.py</files>
  <behavior>
    - Test 1 (RED -> GREEN): in `test_submit_prompt_title_persists_to_store`, `list_sessions()` called immediately after `submit_prompt` returns (NO sleep) must return the auto-title `"a persistent ti..."` for the active session. Today it returns None (empirically confirmed — title is only persisted by on_turn_complete after the turn finishes).
    - Test 2 (existing, must stay green): `test_submit_prompt_auto_titles_new_session` — 60-char prompt yields `("x" * 15) + "..."` on the in-memory session.
    - Test 3 (existing, must stay green): `test_submit_prompt_title_uses_first_line` — multi-line prompt titles from the first line only.
  </behavior>
  <action>
    RED first — strengthen the existing regression test in `tests/test_runtime.py`:
    In `test_submit_prompt_title_persists_to_store` (L203-215), delete the line `await asyncio.sleep(0.3)` so the assertion runs immediately after `submit_prompt` returns. Update the docstring to: "Auto-title reaches disk synchronously in submit_prompt so an immediate list_sessions (TUI refresh path) returns a real name, not None." Keep the `import asyncio` at the top of the file — `test_messages_persist_after_each_turn` (L219) still uses it.
    Run `python -m pytest tests/test_runtime.py::test_submit_prompt_title_persists_to_store -q` — MUST fail (title is None) before any production change. Commit as the failing test if in a TDD flow.

    GREEN — then fix `harness/runtime.py` `submit_prompt` (L82-86): persist the title immediately after setting it, BEFORE dispatching to the scheduler. Insert between the `if session is not None and session.title is None:` block and `await self._scheduler.submit_prompt(prompt)`:

    ```python
    # D-13: persist the auto-title NOW (not just on_turn_complete) so a
    # list_sessions() issued right after the chat RPC resolves (TUI refresh)
    # reads the title from disk instead of None.
    if session is not None and session.title is None:
        session.title = derive_title(prompt)
        await self._session_manager.save_session()
    ```

    Note the save is placed BEFORE `await self._scheduler.submit_prompt(prompt)` — the scheduler's turn task is created by that call, so the synchronous save can never race the turn's message appends. The later `on_turn_complete` save appends only unpersisted events (store.save meta_changed/new_events paths, session/store.py L52-71). The `if session.title is None` guard means this fires once per session — a second prompt never re-saves or clobbers the title (empirically verified).
  </action>
  <verify>
    <automated>python -m pytest tests/test_runtime.py -q</automated>
  </verify>
  <acceptance_criteria>
    - `harness/runtime.py` contains `await self._session_manager.save_session()` inside the `submit_prompt` title block (grep: `rg -n -A3 "session.title = derive_title" harness/runtime.py`)
    - `tests/test_runtime.py` `test_submit_prompt_title_persists_to_store` contains no `asyncio.sleep` (grep: `rg -n -B2 -A2 "asyncio.sleep" tests/test_runtime.py` — remaining sleeps are only in `test_messages_persist_after_each_turn` and `test_scheduler_agent_tracks_active_session_after_create`, never inside the title-persists test)
    - `python -m pytest tests/test_runtime.py -q` → 15 passed
  </acceptance_criteria>
  <done>
    The auto-title is persisted synchronously in `submit_prompt`; the no-sleep regression test passes deterministically; full test_runtime suite green
  </done>
</task>

<task type="auto">
  <name>task 01-2: refresh sessions after /new and after each submitPrompt</name>
  <files>tui-ink/src/app.tsx</files>
  <action>
    Edit `tui-ink/src/app.tsx` InputBar (L28-81). Add a refresh helper immediately after the `useFocus` line (L31), inside the component body:

    ```typescript
    // Refresh the sessions array from disk so panel titles (auto-title included)
    // update without a manual session switch. sessions.list is a disk read —
    // submit_prompt persists the auto-title synchronously (backend fix, task 1).
    const refreshSessions = () =>
      client.listSessions().then((sessions) => {
        useAgentStore.getState().setSessions(sessions)
      })
    ```

    Then update the three branches of the `useInput` handler:

    1. **`/new` branch (L42-48)** — chain a refresh after createSession so the new session is in the store's `sessions` array immediately:
    ```typescript
    } else if (trimmed === "/new") {
      // D-11/D-12: immediate fresh start — create, switch active, clear view. No confirm.
      client.createSession().then((id) => {
        const store = useAgentStore.getState()
        store.setActiveSession(id)
        store.resetConversation()
        return client.listSessions()
      }).then((sessions) => {
        useAgentStore.getState().setSessions(sessions)
      })
    ```
    (The inner callback returns the `listSessions()` promise so the outer `.then` receives the sessions array. The new session has `title=None` at this point — the panel correctly shows "untitled".)

    2. **`/sessions` branch (L49-52)** — refactor to the helper (behavior unchanged):
    ```typescript
    } else if (trimmed === "/sessions") {
      refreshSessions()
    }
    ```

    3. **submit branch (L54)** — chain a refresh after the chat RPC resolves. Because the backend now persists the auto-title before the chat response is sent (task 1), this `listSessions()` deterministically reads the title:
    ```typescript
    } else {
      client.submitPrompt(trimmed).then(refreshSessions)
    }
    ```

    Do NOT touch: the `turn_started`/`token`/`response_complete` event handling in `rpc-client.ts` (unchanged — events keep driving the conversation), the truncation logic (derive_title is backend-side, 15 chars + "...", per D-13), or the startup refresh in `App` (L97-106, already refreshes on connect). Error handling style matches existing branches (no `.catch`) — backend errors already surface via the `error` RPC event.
  </action>
  <verify>
    <automated>npm run typecheck; if ($?) { npm run build }</automated>
  </verify>
  <acceptance_criteria>
    - `tui-ink/src/app.tsx` contains `client.submitPrompt(trimmed).then(refreshSessions)` (grep: `rg -n "submitPrompt\(trimmed\)\.then" tui-ink/src/app.tsx`)
    - `tui-ink/src/app.tsx` contains `return client.listSessions()` inside the `/new` branch and `refreshSessions` defined once (grep: `rg -n "refreshSessions|return client.listSessions" tui-ink/src/app.tsx`)
    - `npm run typecheck` exits 0 (run in `tui-ink/`)
    - `npm run build` exits 0 (run in `tui-ink/`)
  </acceptance_criteria>
  <done>
    Sessions refresh after /new (new session appears as "untitled") and after each submit (auto-title appears immediately); typecheck + build green
  </done>
</task>

<task type="checkpoint:human-verify" gate="blocking">
  <name>task 01-3: human E2E — title appears on first question without switching</name>
  <files>tui-ink/src/app.tsx, harness/runtime.py</files>
  <what-built>
    Backend auto-title now persists synchronously in submit_prompt (task 1) and the TUI refreshes its sessions array after /new and after each prompt submit (task 2), so the conversation panel / header / date panel show the session title as soon as the user asks the first question.
  </what-built>
  <how-to-verify>
    1. Build and launch: `cd tui-ink; npm run build; if ($?) { npm run start }` (from repo root; the RPC backend spawns automatically via `main.py --rpc`).
    2. **/new shows untitled (D-11/D-12):** Type `/new` + Enter — the conversation clears to the empty state and the conversation panel header, top Header, and right DatePanel all show `untitled` (NOT the name of the previous session).
    3. **First question auto-titles (D-13):** Type a prompt longer than 15 characters, e.g. "refactor the session persistence layer please", and press Enter. As soon as the assistant starts responding (or immediately after), the conversation panel header must show `refactor the se...` (first line, 15 chars + "...") WITHOUT opening /session or switching. The Header and DatePanel show the same title.
    4. **No clobber:** Submit a second prompt — the title must remain `refactor the se...` (unchanged).
    5. **Short prompt, no ellipsis:** Run `/new` again, type a short prompt (e.g. "hi") — the panel title becomes `hi` (no "...").
    6. **Persists across restart:** Quit (q), relaunch `npm run start`, type `/session` — both sessions appear in the picker with their auto-titles.
  </how-to-verify>
  <verify>
    <automated>python -m pytest tests/test_runtime.py -q; npm run typecheck</automated>
    Manual: 6-step human checklist above (launch via `npm run start` in `tui-ink/`)
  </verify>
  <done>Conversation panel, Header, and DatePanel all show the auto-title immediately after the first question — no session switch required; title persists across restart; second prompt doesn't clobber it</done>
  <resume-signal>Type "approved" if all 6 checks pass, or describe what failed</resume-signal>
</task>

</tasks>

<threat_model>
## Trust Boundaries

| Boundary | Description |
|----------|-------------|
| TUI → RPC | The chat submit path now issues one additional `sessions.list` RPC after each prompt; `/new` issues one after create. No new input surface — these are local JSON-RPC calls over the existing stdin/stdout channel. |

## STRIDE Threat Register

| Threat ID | Category | Component | Disposition | Mitigation Plan |
|-----------|----------|-----------|-------------|-----------------|
| T-260801-01 | DoS | Extra `sessions.list` RPC per submit | accept | One additional local JSON-RPC request per user Enter press, bounded by human typing rate; single-user local tool; the 30s request timeout (rpc-client.ts L94-99) already bounds hangs. Not an amplification vector |
| T-260801-02 | Information disclosure | Refreshed session summaries (titles) in ConversationPanel/Header/DatePanel | accept | Identical trust model to the existing `/sessions` picker and Header, which already render all session titles. Single-user local tool; no new exposure |
| T-260801-03 | Tampering | `save_session()` rewrite in `submit_prompt` racing the turn's event append | mitigate | The save is awaited BEFORE `await self._scheduler.submit_prompt(prompt)` (task 1), so the turn task does not exist yet when the meta line is rewritten. `store.save` handles the meta_changed path by rewriting the snapshot line then re-appending all events (session/store.py L59-65); the later on_turn_complete save appends only `unpersisted_events()`. All saves are awaited sequentially on the single event loop — no threads, no concurrent file access. Guarded by the `if session.title is None` check (fires once per session) |
</threat_model>

<verification>
- `python -m pytest tests/test_runtime.py -q` (repo root) → 15 passed, including the no-sleep immediate-persistence regression test
- `python -m pytest -q` (repo root) → full suite stays green (54 tests)
- `npm run typecheck` (in `tui-ink/`) → 0 errors
- `npm run build` (in `tui-ink/`) → dist emits
- Grep gates: `submitPrompt(trimmed).then` in app.tsx; `save_session()` in runtime.py's submit_prompt; no `asyncio.sleep` inside the title-persists test
- Human E2E (task 01-3): 6-step checklist
</verification>

<success_criteria>
- Backend: auto-title is persisted synchronously in `submit_prompt` — an immediate `list_sessions()` after the chat RPC resolves returns the derived title (verified by the no-sleep regression test)
- TUI: `sessions` refreshes after `/new` (new session visible as "untitled") and after every submit (auto-title visible without switching sessions)
- ConversationPanel, Header, and DatePanel all show the truncated auto-title (first line, ≤15 chars + "...", D-13 truncation logic unchanged) on the first question
- Second prompt does not clobber the title; titles persist across restart
- All automated checks green; human E2E approved
</success_criteria>

<output>
After completion, create `.planning/quick/260801-jra-when-new-session-is-launched-its-name-is/260801-jra-SUMMARY.md`
</output>
