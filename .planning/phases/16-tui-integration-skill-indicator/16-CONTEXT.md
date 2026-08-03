# Phase 16: TUI Integration (Skill Indicator) - Context

**Gathered:** 2026-08-03
**Status:** Ready for planning

<domain>
## Phase Boundary

The TUI surfaces skill activity: `/skill <name>` works from the TUI input bar and a visible "Skill loaded" indicator appears whenever a skill loads — driven by a typed `skill_loaded` notification, never by inference or stream pollution (ROADMAP criterion 4). This covers the TUI layer only: the typed notification across the full five-touchpoint contract, the input-bar intercept, and the footer indicator. The `skills.load` RPC method, `{skill, status}` ack contract, and loaded-skill accounting already shipped in Phase 15; the backend `load_skill()` shared path and `read_skill` provider shipped in Phase 14; allowed-tools enforcement is Phase 17.

</domain>

<decisions>
## Implementation Decisions

### Indicator form & placement
- **D-01:** "Skill loaded" is a **persistent footer chip**, not a transient inline notice. It stays visible for the whole session and clears on `/new` (loaded skills are session-scoped, ACT-05). Matches the roadmap's "footer chip" wording and the reality that loaded bodies persist in context.
- **D-02:** The chip lives on a **dedicated line above the existing footer hint row** (e.g. `Skill: demo-greeter · weather` above `[/session] sessions [/new] new chat ...`). Hints stay; the chip line appears/disappears as skills load/unload.

### Multiple loaded skills
- **D-03:** The chip shows **all loaded skill names** (comma/separator-joined), not just the most recent. Transparency: every loaded body stays in context for the session, and Phase 17 combines loaded skills' `allowed-tools` via intersection — the user should see every active skill.

### /skill TUI feedback
- **D-04:** `/skill <name>` in the TUI input bar shows an **inline notice for every outcome**, mirroring the REPL ack wording: `Loaded skill <name>` (success), `Skill '<name>' already loaded` (already_loaded), `Skill '<name>' not found` (not_found / SKILL_NOT_FOUND error). The footer chip also updates on a real load.
- **D-05:** A **bare `/skill`** (no argument) shows a usage notice (e.g. `Usage: /skill <name>`) and is **never forwarded as a chat prompt** — same no-fall-through rule as the REPL (15-CONTEXT D-02). All `/skill` input is intercepted like `/session`/`/new`.

### Notification contract (five touchpoints)
- **D-06:** The `skill_loaded` notification payload is **`{ skill: <canonical name> }` only** — no status field. Status lives solely in the `skills.load` RPC response (`loaded|already_loaded|not_found`, 15-CONTEXT D-06). Lean payload, one source of truth per concern.
- **D-07:** The notification fires from the **single shared `load_skill()` path** in `harness/runtime.py`, so both model-driven (`read_skill`) and user-driven (`/skill`) loads emit it — activation cannot drift (15-CONTEXT D-07). `already_loaded` returns early in `load_skill` and emits no notification (nothing changed; the chip already shows the skill).
- **D-08:** The typed event spans all five touchpoints (ROADMAP 16-01): new harness event → server mapping + payload extractor → `NotificationType.skill_loaded` → `handleEvent` switch → store `loadedSkills` state. Notification-driven only — the `skill_name` message-tag detection idea from 14-CONTEXT D-08 is superseded by the typed event.

### Restore / session-switch sync
- **D-09:** The chip reflects **live `skill_loaded` events only**, seen by this TUI instance. It clears on `/new` and on session switch (loaded skills are session-scoped anyway — a switched-to session starts with an empty chip). **No new RPC surface** exposing backend `skill_state`; re-syncing loaded skills across restarts is explicitly out of scope.

### OpenCode's Discretion
- Exact chip styling (colors, separator/icon, truncation when many skills) and footer layout details
- `SkillLoadedEvent` dataclass field names and exact payload-extractor implementation in `server.py`
- Exact usage-line wording and notice styling (beyond the given examples)
- Whether the notice for `/skill` reuses the existing `addNotice` role or a dedicated variant
- How `loadedSkills` is stored in the zustand store (array shape, reset semantics)

</decisions>

<canonical_refs>
## Canonical References

**Downstream agents MUST read these before planning or implementing.**

### Phase goal & requirements (authoritative scope)
- `.planning/ROADMAP.md` §Phase 16 — Goal, success criteria 1-4, and the three planned plans (16-01 notification contract, 16-02 input intercept, 16-03 indicator UI + round-trip test)
- `.planning/REQUIREMENTS.md` §ACT-06 — "TUI shows a visible indicator when a skill is loaded" (this phase's requirement)

### Prior phase context (locked contracts)
- `.planning/phases/15-session-behavior-skill-command/15-CONTEXT.md` — D-05/D-06 (`skills.load` RPC + `{skill, status}` ack), D-07 (REPL calls `load_skill` directly; shared path), D-08 (structured error codes) — the contract Phase 16 consumes
- `.planning/phases/14-read-skill-provider-e2e/14-CONTEXT.md` — D-08 `skill_name` message tag (superseded by typed event, D-06 here); D-07 exactly-once dedup
- `.planning/phases/12-skills-discovery-manifest/12-CONTEXT.md` — D-06 win32 case-insensitive name matching (`/skill` name matching inherits this)
- `.planning/MILESTONE-CONTEXT.md` — D-14 "TUI shows a visible indicator when a skill loads", D-11 user-invocable `/skill`

### Backend implementation (Phase 15 code)
- `harness/runtime.py` §`load_skill` (lines 178-213) — the single shared load path where the new `SkillLoadedEvent` is emitted; already returns "already loaded" no-op (D-07)
- `harness/events.py` — existing `HarnessEvent` subclasses + `EVENT_*` constants; a new `SkillLoadedEvent` + `EVENT_SKILL_LOADED` land here
- `backend/rpc/protocol.py` — `NotificationType` enum (add `skill_loaded`), `EventPayload`, `RPCError`, error codes
- `backend/rpc/server.py` — `_DOMAIN_TO_NOTIFICATION` map, `_PAYLOAD_EXTRACTORS`, `subscribe`/`unsubscribe` lists — the mapping + extractor touchpoints
- `backend/rpc/adapter.py` §`handle_skills_load` (lines 99-111) — existing `skills.load` handler with SKILL_NOT_FOUND mapping

### TUI implementation (this phase)
- `tui-ink/src/bridge/rpc-client.ts` — `loadSkill()` already exists (line 140); `handleEvent` switch (line 199) gets the `skill_loaded` case
- `tui-ink/src/types.ts` — `EventPayload` union (add `skill_loaded`), `SkillLoadedPayload`; `SkillLoadStatus`/`SkillLoadResult` already defined
- `tui-ink/src/store/agent-store.ts` — zustand store; add `loadedSkills` state + reset semantics
- `tui-ink/src/app.tsx` §`InputBar` (lines 28-90) — the `/session`/`/new`/`/sessions` intercept the `/skill` branch joins
- `tui-ink/src/components/footer.tsx` — the hint row the chip line joins (D-02)
- `tui-ink/src/components/message.tsx` — the notice message role `/skill` outcome notices render through (D-04)

</canonical_refs>

<code_context>
## Existing Code Insights

### Reusable Assets
- `RpcClient.loadSkill()` (`rpc-client.ts:140`) — already wired to `skills.load`; the InputBar `/skill` branch calls this directly
- `addNotice` / `notice` message role (`agent-store.ts:170`, `Message.role` in `types.ts`) — the existing "Cancelled" notice pattern `/skill` outcome notices reuse
- `NotificationType` enum + `_DOMAIN_TO_NOTIFICATION` + `_PAYLOAD_EXTRACTORS` (`protocol.py`, `server.py`) — the 5-touchpoint pattern a `skill_loaded` notification follows exactly (D-08)
- `RuntimeAPI.load_skill()` (`runtime.py:178`) — the emission point that covers both `read_skill` and `/skill` (D-07)
- InputBar `useInput` intercept (`app.tsx:41`) — the `/session`/`/new`/`/sessions` dispatch the `/skill` branch mirrors (D-05)

### Established Patterns
- Five-touchpoint typed notification: harness event → server mapping+extractor → protocol → `handleEvent` → store (Phase 9 D-09 pattern, extended per event type)
- Slash-command intercept: input matched exactly, handled inline, never falls through to `submitPrompt`
- Short-ack results (14-CONTEXT D-05 / 15-CONTEXT D-01): acknowledge without echoing body content
- Session-scoped state: `skill_state` on the backend, `loadedSkills` on the TUI — both reset on `/new`
- Case-insensitive win32 name matching (12-CONTEXT D-06) — `/skill` TUI lookup inherits

### Integration Points
- `harness/runtime.py` `load_skill` — emit `SkillLoadedEvent` after successful injection (and only then; no-op on already_loaded/cap-refusal)
- `harness/events.py` — new `SkillLoadedEvent` dataclass + `EVENT_SKILL_LOADED` constant
- `backend/rpc/server.py` — add `EVENT_SKILL_LOADED` to `_DOMAIN_TO_NOTIFICATION`, a `_extract_skill_loaded_payload`, subscribe/unsubscribe in `start()`/`shutdown()`
- `backend/rpc/protocol.py` — add `skill_loaded` to `NotificationType`
- `tui-ink/src/bridge/rpc-client.ts` `handleEvent` — `skill_loaded` case → `store.addLoadedSkill(name)`
- `tui-ink/src/types.ts` — `SkillLoadedPayload`, add to `EventPayload` union
- `tui-ink/src/store/agent-store.ts` — `loadedSkills: string[]`, `addLoadedSkill`, reset on `resetConversation`/session switch
- `tui-ink/src/app.tsx` `InputBar` — `/skill` + bare `/skill` branch (call `loadSkill`, render notice, usage for bare)
- `tui-ink/src/components/footer.tsx` — chip line above hints rendering `loadedSkills`

</code_context>

<specifics>
## Specific Ideas

- The indicator mirrors the REPL ack wording exactly (`Loaded skill <name>` / `Skill '<name>' already loaded` / `Skill '<name>' not found`) — one dedup contract, two entry points, consistent output style
- Chip shows every loaded skill because all bodies stay in context for the session and Phase 17 combines their `allowed-tools` — the user should always see which skills are active
- `/skill` in the TUI should feel exactly like `/session`/`/new` — keyboard-first, immediate, never a chat fall-through

</specifics>

<deferred>
## Deferred Ideas

- **Backend `skill_state` sync over RPC** (chip re-populates on session switch / reconnect) — rejected in D-09; adds a new RPC surface beyond ACT-06
- **`/skills` listing command** (AUTH-02, v1.2) — already deferred from Phase 15; not part of the `/skill` input-bar work
- **Skill indicator in the tool-monitor panel** — the footer chip (D-01/D-02) is the chosen home; tool-monitor stays tool-call-focused
- **Skill unload / removal UX** — skills are session-scoped and cleared only by `/new`; no per-skill unload in this phase

---

*Phase: 16-tui-integration-skill-indicator*
*Context gathered: 2026-08-03*
