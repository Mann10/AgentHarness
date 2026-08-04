# Phase 16: TUI Integration (Skill Indicator) - Research

**Researched:** 2026-08-03
**Domain:** Ink TUI + typed JSON-RPC notification wiring (Python backend / TypeScript frontend)
**Confidence:** HIGH (all five touchpoints verified against live code; test-infra constraint verified against installed packages)

<user_constraints>
## User Constraints (from CONTEXT.md)

### Locked Decisions

#### Indicator form & placement
- **D-01:** "Skill loaded" is a **persistent footer chip**, not a transient inline notice. It stays visible for the whole session and clears on `/new` (loaded skills are session-scoped, ACT-05). Matches the roadmap's "footer chip" wording and the reality that loaded bodies persist in context.
- **D-02:** The chip lives on a **dedicated line above the existing footer hint row** (e.g. `Skill: demo-greeter · weather` above `[/session] sessions [/new] new chat ...`). Hints stay; the chip line appears/disappears as skills load/unload.

#### Multiple loaded skills
- **D-03:** The chip shows **all loaded skill names** (comma/separator-joined), not just the most recent. Transparency: every loaded body stays in context for the session, and Phase 17 combines loaded skills' `allowed-tools` via intersection — the user should see every active skill.

#### /skill TUI feedback
- **D-04:** `/skill <name>` in the TUI input bar shows an **inline notice for every outcome**, mirroring the REPL ack wording: `Loaded skill <name>` (success), `Skill '<name>' already loaded` (already_loaded), `Skill '<name>' not found` (not_found / SKILL_NOT_FOUND error). The footer chip also updates on a real load.
- **D-05:** A **bare `/skill`** (no argument) shows a usage notice (e.g. `Usage: /skill <name>`) and is **never forwarded as a chat prompt** — same no-fall-through rule as the REPL (15-CONTEXT D-02). All `/skill` input is intercepted like `/session`/`/new`.

#### Notification contract (five touchpoints)
- **D-06:** The `skill_loaded` notification payload is **`{ skill: <canonical name> }` only** — no status field. Status lives solely in the `skills.load` RPC response (`loaded|already_loaded|not_found`, 15-CONTEXT D-06). Lean payload, one source of truth per concern.
- **D-07:** The notification fires from the **single shared `load_skill()` path** in `harness/runtime.py`, so both model-driven (`read_skill`) and user-driven (`/skill`) loads emit it — activation cannot drift (15-CONTEXT D-07). `already_loaded` returns early in `load_skill` and emits no notification (nothing changed; the chip already shows the skill).
- **D-08:** The typed event spans all five touchpoints (ROADMAP 16-01): new harness event → server mapping + payload extractor → `NotificationType.skill_loaded` → `handleEvent` switch → store `loadedSkills` state. Notification-driven only — the `skill_name` message-tag detection idea from 14-CONTEXT D-08 is superseded by the typed event.

#### Restore / session-switch sync
- **D-09:** The chip reflects **live `skill_loaded` events only**, seen by this TUI instance. It clears on `/new` and on session switch (loaded skills are session-scoped anyway — a switched-to session starts with an empty chip). **No new RPC surface** exposing backend `skill_state`; re-syncing loaded skills across restarts is explicitly out of scope.

#### OpenCode's Discretion
- Exact chip styling (colors, separator/icon, truncation when many skills) and footer layout details
- `SkillLoadedEvent` dataclass field names and exact payload-extractor implementation in `server.py`
- Exact usage-line wording and notice styling (beyond the given examples)
- Whether the notice for `/skill` reuses the existing `addNotice` role or a dedicated variant
- How `loadedSkills` is stored in the zustand store (array shape, reset semantics)

#### Deferred Ideas (OUT OF SCOPE)
- **Backend `skill_state` sync over RPC** (chip re-populates on session switch / reconnect) — rejected in D-09; adds a new RPC surface beyond ACT-06
- **`/skills` listing command** (AUTH-02, v1.2) — already deferred from Phase 15; not part of the `/skill` input-bar work
- **Skill indicator in the tool-monitor panel** — the footer chip (D-01/D-02) is the chosen home; tool-monitor stays tool-call-focused
- **Skill unload / removal UX** — skills are session-scoped and cleared only by `/new`; no per-skill unload in this phase
</user_constraints>

<phase_requirements>
## Phase Requirements

| ID | Description | Research Support |
|----|-------------|------------------|
| ACT-06 | TUI shows a visible indicator when a skill is loaded | Five-touchpoint `skill_loaded` notification contract fully mapped (below); `/skill` InputBar intercept mirrors `/session`/`/new`; footer chip consumes `loadedSkills` store state; round-trip test structure defined in Validation Architecture |

**Success criteria → evidence mapping (ACT-06):**

| SC | What must be TRUE | Verified mechanism |
|----|-------------------|--------------------|
| 1 | `/skill <name>` loads via backend RPC, never forwarded as prompt | InputBar `useInput` intercept (app.tsx:41-79) — `/skill` branch joins the `/session`/`/new` if/else-if chain before the `else → submitPrompt`; backend `skills.load` → `load_skill_status` already shipped (15-CONTEXT D-05/D-06) |
| 2 | Visible indicator on any load (model-driven OR `/skill`) | `SkillLoadedEvent` emitted from the single shared `load_skill()` (runtime.py:178-213) — covers `read_skill` provider (skills/provider.py:51) and `load_skill_status` RPC (runtime.py:231); footer chip renders `loadedSkills` |
| 3 | Round-trip through typed notification (all five touchpoints) | Full chain verified: `SkillLoadedEvent` → `_DOMAIN_TO_NOTIFICATION` + `_PAYLOAD_EXTRACTORS` (server.py) → `NotificationType.skill_loaded` (protocol.py) → `handleEvent` case (rpc-client.ts) → `addLoadedSkill` (agent-store.ts) |
| 4 | No stream pollution | `handleEvent` `skill_loaded` case touches ONLY `loadedSkills` (chip) — no `addNotice`/`addAssistantMessage`/`addToolCall`; notification payload is `{skill}` only (D-06); Python test asserts no message added to conversation |
</phase_requirements>

## Summary

Phase 16 wires a new typed `skill_loaded` notification through the existing five-touchpoint pipeline (harness event → server mapping + extractor → `NotificationType` → `handleEvent` → zustand store), adds a `/skill` intercept to the Ink InputBar, and renders a persistent footer chip from new `loadedSkills` store state. **Every touchpoint of this pipeline is verified against live code** — this is a mechanical extension of an established pattern (Phase 9 D-09), not a new architecture. The `skills.load` RPC, `{skill, status}` ack, `loadSkill()` client method, and shared `load_skill()` path already exist (Phase 15); Phase 16 adds the notification fan-out and the UI.

**The single most important research finding:** the TUI (`tui-ink/`) has **no automated test infrastructure** — no vitest/jest, no test files, only `npm run typecheck` + `npm run build` + human E2E (verified: package.json scripts, no test dirs; ink-testing-library v4.0.0 is incompatible with installed Ink 7.1.1/React 19.2.8 per Phase 11 research). The "keystroke → RPC → notification → indicator" round-trip therefore splits: **backend touchpoints (1-3) are fully automatable in pytest** (new `tests/test_skill_loaded_notification.py` asserting event emission, dedup, and the exact wire-format JSON the TUI parses); **TUI touchpoints (4-5) are verified via typecheck + build + a blocking human E2E checkpoint** (the established Phase 11 pattern). No new dependencies are introduced — the UI-SPEC's stack (ink 7.1.1, react 19.2.8, zustand 5.0.14, typescript 5.9.3) is confirmed installed.

**Primary recommendation:** Follow the existing extension pattern exactly — one new event dataclass, one enum member, one mapping entry + one extractor, one `handleEvent` case, two store actions — with the emission point locked to runtime.py line 212-213 (after `add_skill_message`, before the return), firing **only** on real loads. Never reuse `addError` for the not-found notice (it sets `status: "error"` and flips the header red — verified). The round-trip test lives in pytest; the TUI side gets a human-E2E plan task mirroring Phase 11's 11-04-03 checkpoint.

**Architecture note:** the UI-SPEC (§6.4) covers the store/component side of the contract; the backend plumbing is "for executor awareness" — but the RESEARCH here confirms the backend emission point must be in `load_skill` itself (not `load_skill_status`), because `load_skill_status` dedup-checks first and then delegates to `load_skill` — a single emission point in `load_skill` covers both RPC and `read_skill` paths with zero duplication.

## Architectural Responsibility Map

| Capability | Primary Tier | Secondary Tier | Rationale |
|------------|-------------|----------------|-----------|
| Skill load + event emission | Backend (harness) | — | `load_skill()` is the single shared path (D-07); the event fires where the load actually completes — covers both `read_skill` and `/skill` |
| Event → notification mapping + payload extraction | Backend (RPC server) | — | `_DOMAIN_TO_NOTIFICATION` / `_PAYLOAD_EXTRACTORS` are the server's forwarders; extractor is the only place `{skill}`-only is enforced (D-06) |
| Notification type contract | Backend (RPC protocol) | — | `NotificationType` enum is the shared wire contract the TUI switch matches on |
| Notification → store mutation | TUI bridge (rpc-client `handleEvent`) | TUI store | The switch owns type→action mapping; store owns the state |
| `loadedSkills` state + chip/notice actions | TUI store (zustand) | — | Footer consumes `loadedSkills`; `addSkillNotice` pushes into `conversation` |
| Footer chip rendering + truncation | TUI components (footer.tsx) | — | Pure view of store state; no business logic |
| `/skill` intercept | TUI app (InputBar `useInput`) | — | Client-side slash command — local, immediate, never leaves the TUI as a prompt (D-05) |
| `/skill` outcome notices | TUI store + message.tsx | — | Notice role message with `tone` renders through the existing MessageCard branch |

**Tier-correctness check (plan-checker):** auth/validation of the skill name is NOT in the TUI — name validation stays backend (`adapter.py` INVALID_PARAMS/SKILL_NOT_FOUND); the TUI passes the raw name (12-CONTEXT D-06 case-insensitive matching is backend-side). No capability is misassigned.

## Standard Stack

### Core

This phase introduces **no new dependencies** (verified: UI-SPEC §12 "no new dependencies — stack unchanged"; nothing needed beyond the installed set).

| Library | Version (installed) | Purpose | Why Standard |
|---------|---------------------|---------|--------------|
| Ink | 7.1.1 [VERIFIED: node_modules] | TUI rendering primitives (`Box`, `Text`, `useInput`, `useWindowSize`) | Existing TUI framework since Phase 9; `useWindowSize` returns `{columns, rows}` [VERIFIED: ink build .d.ts] |
| React | 19.2.8 [VERIFIED: node_modules] | Component model for Ink | Existing |
| zustand | 5.0.14 [VERIFIED: node_modules] | `useAgentStore` state store | Existing; chip state + notice actions live here |
| TypeScript | 5.9.3 [VERIFIED: node_modules] | `npm run typecheck` (strict: true, tsconfig verified) | Existing verification gate |
| tsup | ^8.0.0 | `npm run build` → dist | Existing build |
| pytest | 8.4.2, `asyncio_mode = auto` [VERIFIED: pytest.ini] | Backend test framework | All 23 backend test files use it |
| Python | 3.12.5 [VERIFIED: runtime] | Backend | Existing |

### Supporting

| Library | Version | Purpose | When to Use |
|---------|---------|---------|-------------|
| `unittest.mock` (AsyncMock/MagicMock) | stdlib | Stub LLM/client/registry in tests | Every backend test fixture (test_load_skill.py, test_skills_e2e.py patterns) |
| JSONLSessionStore(tempdir) | project | Isolated session storage in tests | Round-trip test fixture |
| Real `SkillStore` + temp `skills_root` fixture | project | Real skill lookup in tests | Round-trip + dedup tests (test_skills_e2e.py pattern) |

### Alternatives Considered

| Instead of | Could Use | Tradeoff |
|------------|-----------|----------|
| `npm run typecheck` + `npm run build` + human E2E for TUI verification | vitest / jest + ink-testing-library | **Rejected.** ink-testing-library v4.0.0 pins Ink ^5/React 18 — incompatible with Ink 7.1.1/React 19.2.8 [CITED: 11-RESEARCH.md lines 82/117]. Adding a bespoke TS test harness is out of scope and unsupported by any prior phase. |
| pytest round-trip at dispatcher level | Full subprocess spawn (`python main.py --rpc` driven via stdin/stdout) | Subprocess test is slower/flakier and has no precedent in the suite (no test imports RPCServer today). In-process `RPCServer` + monkeypatched `_write_json` gives the same wire-format assertion deterministically. |
| `addSkillNotice` dedicated action | Extend `addNotice` with tone param | UI-SPEC §6.3 locks the dedicated action name and signature. Extending `addNotice` would touch the "Cancelled" path (rpc-client.ts:276) for zero benefit. |

**Version verification:** All versions confirmed against `node_modules`/registry on 2026-08-03 (see Sources). Training-data knowledge was not relied on for any version claim.

## Architecture Patterns

### System Architecture Diagram

```
                        ┌─────────────────────────────────────────────────────────┐
                        │                     TUI (tui-ink/)                        │
                        │                                                          │
   keystroke ──► ┌─────────────┐   JSON-RPC req   ┌──────────────┐                 │
   "/skill x"    │ InputBar     │ ───────────────► │ rpc-client.ts │                │
                 │ useInput     │                  │ request()    │                │
                 │ (app.tsx:41) │                  │ loadSkill()   │                │
                 └──────┬──────┘                  └──────┬───────┘                │
                        │ no fall-through (D-05)         │  skills.load            │
                        │                                ▼                        │
                 addSkillNotice ◄── ack {skill,status}   ┌──────────────┐          │
                 (notice msgs)   ◄── or RPC error         │ handleEvent  │          │
                        ▲                                │ switch       │          │
                        │                                │ (rpc:207)    │          │
                        │            NDJSON notification  │              │          │
                        └── conversation ◄──(notice)───── └──────┬───────┘          │
                        ▲                                        │ "skill_loaded"   │
                        │                                        ▼                  │
                 ┌─────────────┐   {skill: name}   ┌──────────────┐                 │
                 │ Footer chip │ ◄──loadedSkills──  │ agent-store  │ ◄─ addLoadedSkill
                 │ (footer.tsx)│   (zustand)        │ loadedSkills │   (chip only)
                 └─────────────┘                    └──────────────┘                 │
                        └─────────────────────────────────────────────────────────┘

   Python backend (subprocess, NDJSON over stdio):
   ┌──────────────┐     ┌───────────────┐     ┌──────────────────┐     ┌───────────────┐
   │ main.py --rpc │ ──► │ RPCServer     │ ──► │ EventBus         │ ◄── │ runtime.py    │
   │ run_rpc()    │     │ _on_event     │     │ publish()        │     │ load_skill()  │
   └──────────────┘     │ (server.py)   │     └────────▲─────────┘     │ (runtime:178) │
                        │ _DOMAIN_TO_   │              │ EventBus       └───────┬───────┘
                        │  NOTIFICATION │              │ publish            │ add_skill_message
                        │ _PAYLOAD_     │              │                    │ (context:212)
                        │  EXTRACTORS   │              │                    ▼
                        └───────────────┘    SkillLoadedEvent ◄── emit ── only on real load
                                            (events.py, after inject, before return)

   Wire format (what the TUI's handleEvent parses):
   {"jsonrpc":"2.0","method":"event",
    "params":{"type":"skill_loaded","request_id":"<session_id>",
              "payload":{"skill":"demo-greeter"}}}
```

**Trace of the primary use case (SC-3):** user types `/skill demo-greeter` + Enter → InputBar matches `SKILL_CMD` regex → `client.loadSkill(name)` writes `{"method":"skills.load","params":{"name":...}}` to stdin → adapter `handle_skills_load` → `runtime.load_skill_status` → dedup check → `load_skill` (shared path) → body injected (`add_skill_message`) → **`SkillLoadedEvent` published** → RPCServer `_on_event` → `_event_to_notification` (mapping + extractor) → NDJSON notification written → TUI line handler → `handleMessage` (no `id` → event branch) → `handleEvent` `skill_loaded` case → `store.addLoadedSkill(p.skill)` → chip re-renders. Meanwhile the RPC response `{skill, status: loaded}` resolves the pending promise → InputBar `.then` → `addSkillNotice("Loaded skill demo-greeter", "success")` → notice message rendered by MessageCard. **The notification is written before the RPC response on the wire** (it fires inside the `await` of `load_skill`); the TUI treats them as independent — no ordering dependency.

### Recommended Project Structure

```
harness/events.py                    MOD  SkillLoadedEvent + EVENT_SKILL_LOADED (touchpoint 1)
harness/runtime.py                   MOD  emit after add_skill_message (runtime.py:212→213)
harness/__init__.py                  MOD  (optional) export new event + constant in __all__
backend/rpc/protocol.py              MOD  NotificationType.skill_loaded (touchpoint 3)
backend/rpc/server.py                MOD  _DOMAIN_TO_NOTIFICATION + _PAYLOAD_EXTRACTORS + subscribe/unsubscribe (touchpoint 2)
tui-ink/src/types.ts                 MOD  SkillLoadedPayload + EventPayload union + Message.tone + AgentState.loadedSkills
tui-ink/src/bridge/rpc-client.ts     MOD  handleEvent case (touchpoint 4)
tui-ink/src/store/agent-store.ts     MOD  loadedSkills + addLoadedSkill + addSkillNotice + reset in both reset paths
tui-ink/src/app.tsx                  MOD  InputBar /skill branches (bare + <name>)
tui-ink/src/components/footer.tsx    MOD  chip row above hints + truncation
tui-ink/src/components/message.tsx   MOD  notice tone rendering (✓/✗/info)
tests/test_skill_loaded_notification.py  NEW  backend round-trip + wire-format tests
```

### Pattern 1: Five-Touchpoint Typed Notification (D-08)
**What:** Every domain event follows: harness event dataclass → server mapping (`_DOMAIN_TO_NOTIFICATION`) + payload extractor (`_PAYLOAD_EXTRACTORS`) → `NotificationType` enum → TUI `handleEvent` switch → store mutation. Verified against all 7 existing event types in `backend/rpc/server.py` (lines 53-123, 161-183) and `tui-ink/src/bridge/rpc-client.ts` (lines 207-281).
**When to use:** Any new notification type. Phase 16 adds the 8th.
**Extension checklist (the exact 5 edits for a new event):**
1. `harness/events.py` — dataclass + `EVENT_*` constant (name = class name, per `EventBus.publish` routing by `type(event).__name__`).
2. `backend/rpc/server.py` — import both; add mapping entry + `_extract_skill_loaded_payload` + extractor entry; add `subscribe`/`unsubscribe` lines in `start()`/`shutdown()`.
3. `backend/rpc/protocol.py` — enum member.
4. `tui-ink/src/bridge/rpc-client.ts` — switch case.
5. `tui-ink/src/store/agent-store.ts` (+ `types.ts`) — state + action.
**Example (extractor — server.py pattern, from lines 106-111):**
```python
def _extract_skill_loaded_payload(event: SkillLoadedEvent) -> dict:
    """D-06: payload is {skill: canonical name} ONLY — no status."""
    return {"skill": event.skill}
```

### Pattern 2: Slash-Command Intercept, Never Fall-Through (D-05)
**What:** `InputBar` `useInput` on `key.return` matches exact trimmed input, handles inline, clears input, returns — `submitPrompt` is only reached in the final `else`. Verified: app.tsx:45-67 (`/session`, `/new`, `/sessions` branches).
**When to use:** Any new TUI slash command. The `/skill` branch slots into the existing if/else-if chain.

### Anti-Patterns to Avoid
- **Emitting the event from `load_skill_status` instead of `load_skill`:** `load_skill_status` (runtime.py:215-232) dedup-checks then delegates to `load_skill`. Emitting in `load_skill_status` would create a second emission point and risk double events; emitting in `load_skill` alone covers both RPC and `read_skill` paths.
- **Emitting before the load completes / on refusal paths:** the event must fire strictly after `add_skill_message` (runtime.py:212) and never on `already_loaded` (195-196), `KeyError` (192), or cap-refusal (204-207) — otherwise the chip lies about what's in context.
- **Reusing `addError` for `/skill not_found`:** `addError` sets `status: "error"` (agent-store.ts:178-185), which flips the Header to red (header.tsx:13) — a failed slash command must not put the app in an error state. UI-SPEC §6.3 locks `addSkillNotice` (never touches status/busy/error).
- **Prefix-greedy `/skill` matching:** `/skills` must fall through to `submitPrompt` (deferred v1.2 command). The locked regex `^\/skill(?:\s+(.+))?$` is anchored and does NOT match `/skills` — never use `startsWith("/skill")`.
- **Stream pollution via the notification:** the `handleEvent` `skill_loaded` case must call only `addLoadedSkill` — no `addNotice`, no `startAssistantMessage`, no `addToolCall` (ROADMAP criterion 4).

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| Notification plumbing | A bespoke event-inference system (e.g. detecting skill bodies in stream) | The typed `skill_loaded` event through the existing pipeline | Inference "worked" in 14-CONTEXT D-08's `skill_name` tag idea and was explicitly superseded (D-06/D-08): inference can't distinguish a real load from a re-send and drifts from the shared path |
| Footer truncation math | Nothing — implement UI-SPEC §6.1 exactly | The locked truncation algorithm (kept + `+N more`, hard floor < ~18 cols) | Contract-locked; no library needed; Ink `Text` will not wrap inside a `Box` with fixed width if we drop names ourselves |
| `/skill` notices | A new message role | Existing `notice` role + `tone` field (UI-SPEC §6.3) | Reuses MessageCard's notice branch; zero new rendering paths |

**Key insight:** This phase has **nothing to hand-roll** — every mechanism (notification pipeline, slash-command intercept, notice role, zustand store) already exists and is verified. The risk is not missing infrastructure; it's **missing an integration point** (e.g. forgetting `loadedSkills: []` in one of the two reset paths, or forgetting `AgentState.loadedSkills` in types.ts so typecheck fails).

## Common Pitfalls

### Pitfall 1: Missing store reset → chip persists across `/new`
**What goes wrong:** The chip still shows skills after `/new` or a session switch, violating D-09.
**Why it happens:** `loadedSkills: []` must be added to **both** `resetConversation()` (agent-store.ts:197-204, the `/new` path at app.tsx:50-55) **and** `loadConversation()` (206-218, the session-switch path via session-picker.tsx:65). `setActiveSession` alone (agent-store.ts:60) is NOT a reset — verified it only sets the id.
**How to avoid:** Plan task must touch both actions; the round-trip test asserts `loadedSkills` is empty after both.
**Warning signs:** Chip visible after `/new`; typecheck passes but behavior wrong.

### Pitfall 2: Wire-order assumption in the round-trip test
**What goes wrong:** A test asserting "RPC response arrives before the notification" fails intermittently.
**Why it happens:** The `SkillLoadedEvent` is published during the `await` inside `load_skill` — RPCServer `_on_event` writes the notification **before** the dispatcher writes the response (response is written only after the whole handler chain returns). Verified ordering at runtime.py:212/231 + server.py:197-233.
**How to avoid:** Assert the two messages independently (response resolves `skills.load`; notification carries `type: "skill_loaded"`). Collect both and filter, never assume order.
**Warning signs:** Flaky ordering assertions.

### Pitfall 3: `AgentState` interface divergence → typecheck break
**What goes wrong:** `npm run typecheck` fails because the store adds `loadedSkills` but `AgentState` (types.ts:97-109) doesn't declare it (`AgentStore = AgentState & AgentActions`, agent-store.ts:41).
**Why it happens:** The UI-SPEC's types.ts list (§6.4) mentions `SkillLoadedPayload`, `EventPayload`, and `Message.tone` but not `AgentState.loadedSkills` — it's implied by the store change.
**How to avoid:** Include `loadedSkills: string[]` in the `AgentState` interface in the plan's interface list.
**Warning signs:** typecheck error "Property 'loadedSkills' is missing in type".

### Pitfall 4: Emitting on the wrong paths
**What goes wrong:** Chip shows a skill that wasn't actually injected (or misses one that was).
**Why it happens:** Emitting before `add_skill_message`, on `already_loaded` (chip already shows it — redundant), or on cap-refusal (load didn't happen).
**How to avoid:** Emission strictly between runtime.py:212 and :213; pytest asserts zero events on `already_loaded`/not_found/cap-refusal.
**Warning signs:** Chip gains a skill on a failed load; duplicate chip entries after double-load.

### Pitfall 5: Header turns red on `/skill not_found`
**What goes wrong:** A failed slash command flips the whole app header to a red error state.
**Why it happens:** `addError` sets `status: "error"`; Header maps error → red (header.tsx:9-14). Using it for the not-found notice is the trap.
**How to avoid:** `addSkillNotice` never touches `status`/`busy`/`error` (locked in UI-SPEC §6.3).
**Warning signs:** Red header after `/skill nope`.

### Pitfall 6: `/skills` accidentally intercepted
**What goes wrong:** `/skills` gets eaten as a `skill` command instead of falling through to chat.
**Why it happens:** A `startsWith("/skill")` or unanchored regex matches `/skills`.
**How to avoid:** Use the locked anchored regex `^\/skill(?:\s+(.+))?$` — verified by regex semantics it cannot match `/skills` (the `s` after `/skill` fails both the end-anchor and the `\s+` alternative). Add a pytest-level comment + human E2E check.
**Warning signs:** `/skills` typed → usage notice instead of a chat message.

### Pitfall 7: Model-driven load renders a notice
**What goes wrong:** When the model calls `read_skill`, a notice or message appears in the stream.
**Why it happens:** The `handleEvent` case calling `addNotice`/`addAssistantMessage` for the chip update.
**How to avoid:** The `skill_loaded` case calls ONLY `addLoadedSkill` (chip). Notices come only from the `/skill` RPC ack path. ROADMAP criterion 4.
**Warning signs:** A `Loaded skill ...` line appears mid-stream after a model turn.

## Code Examples

Verified patterns from official sources (all from the live codebase, paths current as of 2026-08-03):

### 1. New harness event (harness/events.py — touchpoint 1)
```python
@dataclass
class SkillLoadedEvent(HarnessEvent):
    """Emitted when a skill body is injected into context (D-07/D-08).

    Fires ONLY on real loads from the shared load_skill() path — never on
    already_loaded (nothing changed), not_found, or cap refusal (load didn't
    happen). session_id is carried for wire request_id consistency (D-09
    pattern); it is NOT part of the payload (D-06: {skill} only).
    """
    session_id: str = ""
    skill: str = ""


EVENT_SKILL_LOADED = "SkillLoadedEvent"   # name == class name (EventBus routes on type.__name__)
```

### 2. Emission point (harness/runtime.py — inside `load_skill`, after injection)
```python
        # H-03 hardening: mark the record BEFORE the injection await — any
        # concurrent load_skill caller sees the record (no TOCTOU double-inject).
        loaded.append({"name": info.name, "dir": str(info.path), "tokens": body_tokens})
        session.skill_state["loaded"] = loaded
        await session.context.add_skill_message(info.name, body)
        # D-07/D-08: emit ONLY after the body is in context — the chip must
        # never show a skill whose body is not loaded. No event on the
        # already_loaded early-return (:196) or the cap refusal (:204-207).
        await self._event_bus.publish(SkillLoadedEvent(session_id=session.id, skill=info.name))
        return f"Loaded skill {info.name}"             # D-05 short ack
```
(Requires `from harness.events import SkillLoadedEvent` — import alongside the existing `from harness.event_bus import EventBus`.)

### 3. Protocol enum (backend/rpc/protocol.py — touchpoint 3)
```python
class NotificationType(str, Enum):
    """Maps domain event types to notification type strings (D-09)."""
    turn_started = "turn_started"
    tool_call = "tool_call"
    tool_result = "tool_result"
    token = "token"
    response_complete = "response_complete"
    cancelled = "cancelled"
    error = "error"
    skill_loaded = "skill_loaded"      # NEW — D-08
```

### 4. Server mapping + extractor (backend/rpc/server.py — touchpoint 2)
```python
_DOMAIN_TO_NOTIFICATION: dict[str, str] = {
    # ... existing 7 entries ...
    EVENT_SKILL_LOADED: NotificationType.skill_loaded.value,
}

def _extract_skill_loaded_payload(event: SkillLoadedEvent) -> dict:
    """D-06: payload is {skill: canonical name} ONLY — status lives in the RPC ack."""
    return {"skill": event.skill}

_PAYLOAD_EXTRACTORS: dict[str, callable] = {
    # ... existing 7 entries ...
    EVENT_SKILL_LOADED: _extract_skill_loaded_payload,
}

# in start():  await self._event_bus.subscribe(EVENT_SKILL_LOADED, self._on_event)
# in shutdown(): await self._event_bus.unsubscribe(EVENT_SKILL_LOADED, self._on_event)
```
Note: `_event_to_notification` (server.py:202-233) handles request_id automatically — with `session_id` on the event it uses the session id; the extractor only governs `payload`.

### 5. TUI types (tui-ink/src/types.ts)
```ts
export interface SkillLoadedPayload {
  skill: string        // canonical name (D-06: { skill } only)
}

// EventPayload union gains:
//   | { type: "skill_loaded"; payload: SkillLoadedPayload }

export interface Message {
  id: string
  role: "user" | "assistant" | "notice" | "error"
  content: string
  timestamp: number
  isStreaming?: boolean
  truncated?: boolean
  tone?: "success" | "error"      // NEW — notice variants (UI-SPEC §6.3)
}

export interface AgentState {
  // ... existing fields ...
  loadedSkills: string[]          // NEW — consumed by Footer chip (must match store!)
}
```

### 6. handleEvent case (tui-ink/src/bridge/rpc-client.ts — touchpoint 4)
```ts
case "skill_loaded": {
  // D-07/D-08: chip state ONLY — never a notice, never a stream message,
  // never touches status/busy (ROADMAP criterion 4). Model-driven loads
  // must not inject into the conversation.
  const p = payload as { skill: string }
  store.addLoadedSkill(p.skill)
  break
}
```

### 7. Store additions (tui-ink/src/store/agent-store.ts — touchpoint 5)
```ts
// state: loadedSkills: [] as string[]        // canonical names, load order (D-03)

addLoadedSkill: (name) =>
  set((s) =>
    s.loadedSkills.includes(name)
      ? s                                  // belt-and-suspenders; backend dedups (D-07)
      : { loadedSkills: [...s.loadedSkills, name] }
  ),

addSkillNotice: (text, tone) =>
  set((s) => ({
    conversation: [
      ...s.conversation,
      { id: nextId(), role: "notice", content: text, timestamp: now(), ...(tone && { tone }) },
    ],
  })),   // NEVER touches status/busy/error (UI-SPEC §6.3 — addError is NOT reused)

// resetConversation: set({ ..., loadedSkills: [] })   // /new path
// loadConversation:   set({ ..., loadedSkills: [] })  // session-switch path (D-09)
```

### 8. InputBar `/skill` intercept (tui-ink/src/app.tsx — inside `useInput`, `key.return` branch)
```ts
if (trimmed === "/session") {
  onOpenPicker()
} else if (trimmed === "/new") {
  // ... existing ...
} else if (trimmed === "/sessions") {
  refreshSessions()
} else if (SKILL_CMD.test(trimmed)) {
  // Branch gate is the anchored regex ITSELF (research Pitfall 6) — `/skills`
  // fails the test and falls through to the final else → submitPrompt. NOT startsWith.
  const m = trimmed.match(SKILL_CMD)        // /^\/skill(?:\s+(.+))?$/ — non-null here, no /g flag
  const store = useAgentStore.getState()
  const name = m?.[1]?.trim()
  if (!name) {
    store.addSkillNotice(SKILL_USAGE_LINE)  // "Usage: /skill <name>" — info tone (bare, D-05)
  } else {
    client.loadSkill(name)
      .then((result) => {
        // result: { skill: canonical, status: loaded|already_loaded } — 15-CONTEXT D-06
        const s = useAgentStore.getState()
        if (result.status === "loaded") s.addSkillNotice(`Loaded skill ${result.skill}`, "success")
        else s.addSkillNotice(`Skill '${result.skill}' already loaded`)  // info
      })
      .catch((err: Error) => {
        const s = useAgentStore.getState()
        // D-04: SKILL_NOT_FOUND surfaces the BARE verbatim copy — the RPC client
        // rejects with only the message (rpc-client.ts:180) and adapter.py:107
        // builds it from the exact trimmed name, so equality is deterministic.
        if (err.message === `Skill '${name}' not found.`) {
          s.addSkillNotice(`Skill '${name}' not found`, "error")   // D-04 verbatim (no trailing period)
        } else {
          s.addSkillNotice(SKILL_LOAD_FAILED(err.message), "error") // "Failed to load skill: {message}"
        }
      })
  }
} else {
  client.submitPrompt(trimmed).then(refreshSessions)
}
setInput("")
return
```
No `busy` flag during the load (UI-SPEC §6.2 — input stays usable; the ack is fast). The chip does NOT update from this ack — only from the notification (§6.4).

### 9. Footer chip (tui-ink/src/components/footer.tsx — D-02)
```tsx
export function Footer() {
  const loadedSkills = useAgentStore((s) => s.loadedSkills)   // re-renders on chip changes only
  const { columns } = useWindowSize()                          // verified: {columns, rows}

  return (
    <Box flexDirection="column" width="100%">
      {loadedSkills.length > 0 && (
        <Box paddingX={CHIP_PADDING_X}>
          <Text dimColor>{CHIP_LABEL} </Text>                   // "Skill:" dim
          <Text bold color="white">{formatChip(loadedSkills, columns)}</Text>
        </Box>
      )}
      <Box paddingX={CHIP_PADDING_X}>
        {/* existing hint row — untouched */}
      </Box>
    </Box>
  )
}
```
Truncation per UI-SPEC §6.1 (locked): `W = columns - 4`; join all with `" · "`; drop trailing names until `kept + " · +N more"` fits (suffix dim); hard floor — hide the whole row if even `Skill: +{N}` exceeds W.

### 10. MessageCard notice tones (tui-ink/src/components/message.tsx — UI-SPEC §6.3)
```tsx
if (message.role === "notice") {
  if (message.tone === "success") {
    return <Box><Text color="green" bold>{NOTICE_OK} {message.content}</Text></Box>   // ✓
  }
  if (message.tone === "error") {
    return <Box><Text color="red" bold>{NOTICE_ERR} {message.content}</Text></Box>    // ✗
  }
  return (
    <Box>
      <Text dimColor italic>{message.content}</Text>   // existing info style — already loaded / Usage
    </Box>
  )
}
```
Copy strings are locked verbatim (UI-SPEC §11): `Loaded skill <name>`, `Skill '<name>' already loaded`, `Skill '<name>' not found`, `Usage: /skill <name>`, `Failed to load skill: {message}` — `<name>` is the **canonical** name from `result.skill`.

## State of the Art

| Old Approach | Current Approach | When Changed | Impact |
|--------------|------------------|--------------|--------|
| `skill_name` message-tag detection (14-CONTEXT D-08) | Typed `skill_loaded` notification event | Phase 16 (D-08) | Inference-based detection superseded by an explicit event from the shared load path — no drift, no false positives, no stream sniffing |
| TUI has no skill indicator; `/skill` is REPL-only | Footer chip + `/skill` input-bar intercept | Phase 16 | ACT-06 satisfied; TUI matches REPL ack wording (one dedup contract, two entry points) |
| 7 notification types | 8 (adds `skill_loaded`) | Phase 16 | 8th member of the Phase 9 D-09 pattern; same extension mechanism |

**Deprecated/outdated:**
- **`Message.skill_name` tag as an indicator trigger**: the tag remains on the persisted `Message` (Phase 14 plumbing), but it is no longer the TUI's signal source — the typed event is. Do not build detection on it (D-08).

## Assumptions Log

| # | Claim | Section | Risk if Wrong |
|---|-------|---------|---------------|
| A1 | Emitting the event between runtime.py:212 and :213 is safe because `add_skill_message` appends to an in-memory list and cannot realistically fail (no await-able failure path between mark and emit that would leave the body absent) | Code Examples / Pitfall 4 | LOW — if a future injection failure appears after the mark, the event could fire without the body in context; today the ordering mark→inject→emit means the chip can only show skills whose body was added |
| A2 | `useWindowSize` is the right width source for the footer truncation (already used by session-picker for rows) | Code Examples / footer | LOW — verified the hook exists and returns `{columns, rows}` in Ink 7.1.1 build; only the `columns` member usage is new |
| A3 | No TS test runner should be introduced (typecheck + build + human E2E remain the TUI verification bar) | Standard Stack / Validation Architecture | MEDIUM — if the milestone wants durable TUI regression tests, a vitest harness is a follow-up decision; Phase 11 explicitly rejected adding one, and ink-testing-library is incompatible with Ink 7.1 |

## Open Questions (RESOLVED)

1. **Should the `skill_loaded` case also clear duplicate entries in `loadedSkills` on `already_loaded`?** — **RESOLVED:** no additional handling. The store dedup-append is the agreed defensive behavior and the backend never fires the event on `already_loaded` (D-07), so duplicates are impossible by construction.
   - What we know: the backend dedups (D-07) and only fires the event on real loads, so duplicates are impossible by construction; UI-SPEC §6.4 locks the dedup-append as "belt-and-suspenders".
   - What's unclear: nothing material — the store dedup-append is the agreed defensive behavior.
   - Recommendation: implement as spec'd; no additional handling. **(Implemented in 16-01 task 3 — `addLoadedSkill` dedup-append.)**

2. **Does the notification need `session_id` in the payload?** — **RESOLVED:** `session_id` lives on the `SkillLoadedEvent` dataclass for wire `request_id` consistency but stays OUT of the payload — D-06 `{skill}` only.
   - What we know: D-06 locks `{skill}` only; `_event_to_notification` derives `request_id` from `event.session_id` automatically (falling back to `event_id` if absent); the TUI ignores `request_id` in `handleEvent` (verified rpc-client.ts:204 destructures type/payload only).
   - Recommendation: include a `session_id` field on the `SkillLoadedEvent` dataclass (wire-consistent with every other event) but keep it out of the payload. Purely cosmetic; either choice works. **(Implemented in 16-01 tasks 2-3 + `test_payload_is_skill_only`.)**

3. **Where exactly does the human E2E checkpoint live?** — **RESOLVED:** the blocking human E2E is the final task of plan 16-03 (task 3, mirroring 11-04-03); automated pytest covers touchpoints 1-3.
   - What we know: Phase 11 placed a blocking human checkpoint as the final plan task (11-04-03); Phase 16's plan 16-03 includes "round-trip test (keystroke → RPC → notification → indicator)".
   - Recommendation: automated pytest covers touchpoints 1-3; the human E2E (plan 16-03 task, mirroring 11-04-03) covers keystroke → chip and the no-pollution visual check. No open question — just a planning decision to make it blocking. **(Implemented: 16-03 task 3, blocking `checkpoint:human-verify`.)**

## Environment Availability

| Dependency | Required By | Available | Version | Fallback |
|------------|------------|-----------|---------|----------|
| Python | Backend + pytest | ✓ | 3.12.5 | — |
| pytest | Backend tests | ✓ | 8.4.2 (asyncio_mode=auto) | — |
| Node.js | TUI typecheck/build | ✓ | v22.20.0 | — |
| npm | TUI scripts | ✓ | 10.9.3 | — |
| ink | TUI rendering | ✓ | 7.1.1 | — |
| react / zustand / typescript / tsup | TUI | ✓ | 19.2.8 / 5.0.14 / 5.9.3 / ^8 | — |
| Real skills for E2E | Human E2E checkpoint | ✓ | `.agentharness/skills/{demo-greeter, frontend-design}` (demo-greeter has `allowed-tools: [echo]`) | Tests use temp `skills_root` fixture instead |
| TS test runner (vitest/jest) | TUI unit tests | ✗ | — | `npm run typecheck` + `npm run build` + human E2E (established Phase 11 pattern; ink-testing-library incompatible) |

**Missing dependencies with no fallback:** none — every runtime dependency for this phase is present.

**Missing dependencies with fallback:** TS test runner — deliberately not introduced (see Assumptions Log A3); backend round-trip is fully automated in pytest.

## Validation Architecture

> nyquist_validation is enabled (config.json has no `workflow.nyquist_validation` key — absent = enabled).

### Test Framework

| Property | Value |
|----------|-------|
| Framework | pytest 8.4.2 (`asyncio_mode = auto`, `testpaths = tests`) for backend; `tsc --noEmit` + `tsup` for TUI (no TS test runner — Phase 11 precedent) |
| Config file | `pytest.ini`; `tui-ink/tsconfig.json` |
| Quick run command | Backend tasks: `python -m pytest tests/test_skill_loaded_notification.py -x`; TUI tasks: `npm run typecheck` (in `tui-ink/`) |
| Full suite command | `python -m pytest -q` && `npm run typecheck` && `npm run build` (in `tui-ink/`) |

### Validation Dimensions (what "correct" means for Phase 16)

Each ACT-06 success criterion maps to a verifiable dimension:

| Dimension | Success criterion | Automated check (pytest, new file) | Human E2E (plan 16-03, blocking) |
|-----------|-------------------|-------------------------------------|----------------------------------|
| **SC-1: `/skill` intercept** | `/skill <name>` loads via RPC; never forwarded as prompt | Existing `tests/test_skills_load_rpc.py` proves `skills.load` → `{skill,status}` + error codes; regex `^\/skill(?:\s+(.+))?$` excludes `/skills` (verified semantics) | `npm run start` → type `/skill demo-greeter` + Enter → `✓ Loaded skill demo-greeter` notice, chip appears, **no assistant message started**; `/skills` + Enter → treated as chat text |
| **SC-2: indicator on any load** | Chip appears for model-driven AND `/skill` loads | `test_load_skill_emits_skill_loaded_event`: subscribe collector → `runtime.load_skill` → `SkillLoadedEvent(skill="demo-greeter")` received; `test_model_driven_read_skill_emits_event`: via `SkillToolProvider.call_tool("read_skill", ...)` → event received (both paths, D-07) | Model turn calling `read_skill` → chip gains the skill with **no notice, no stream message** |
| **SC-3: five-touchpoint round trip** | keystroke → RPC → load → notification → indicator | `test_event_maps_to_notification_wire_format`: `server._event_to_notification(SkillLoadedEvent(skill=...))` returns exactly `{"jsonrpc":"2.0","method":"event","params":{"type":"skill_loaded","request_id":...,"payload":{"skill":"demo-greeter"}}}`; `test_skills_load_rpc_round_trip_emits_notification`: real RPCServer + dispatcher, monkeypatched `_write_json` collector → dispatch `skills.load` → response `{skill, status:"loaded"}` **and** one `skill_loaded` notification with `payload == {"skill": "demo-greeter"}` (assert messages independently — no order assumption, Pitfall 2) | Full keystroke → chip visual check |
| **SC-4: no stream pollution** | No fake tool cards, no streamed chunks, no smuggling | `test_load_skill_adds_no_conversation_message`: after load, `to_llm_messages()` gains exactly the system body (no user/assistant); `test_payload_is_skill_only`: notification payload has exactly the `skill` key (D-06); `test_already_loaded_emits_no_event` / `test_not_found_emits_no_event` / `test_cap_refusal_emits_no_event`: zero events on no-op/error paths | No `✓ Loaded skill` line appears mid-stream on a model-driven load; no tool card appears for the notification |

### Phase Requirements → Test Map

| Req ID | Behavior | Test Type | Automated Command | File Exists? |
|--------|----------|-----------|-------------------|-------------|
| ACT-06 | `skill_loaded` event fires on real load (both paths) | unit/integration | `python -m pytest tests/test_skill_loaded_notification.py -k "emits" -x` | ❌ Wave 0 |
| ACT-06 | No event on already_loaded / not_found / cap-refusal | unit | `python -m pytest tests/test_skill_loaded_notification.py -k "no_event" -x` | ❌ Wave 0 |
| ACT-06 | Wire format `{type:"skill_loaded", payload:{skill}}` | unit | `python -m pytest tests/test_skill_loaded_notification.py -k "wire_format" -x` | ❌ Wave 0 |
| ACT-06 | RPC `skills.load` round trip emits the notification | integration | `python -m pytest tests/test_skill_loaded_notification.py -k "round_trip" -x` | ❌ Wave 0 |
| ACT-06 | No conversation/tool-call pollution on load | unit | `python -m pytest tests/test_skill_loaded_notification.py -k "pollution" -x` | ❌ Wave 0 |
| ACT-06 | TUI compiles with new types/actions/cases | typecheck | `npm run typecheck` (in `tui-ink/`) | ✅ (tsconfig exists) |
| ACT-06 | Chip + notices render, `/skill` never falls through | human E2E (blocking) | `npm run start` (in `tui-ink/`, manual — 11-04-03 pattern) | — |

### Sampling Rate
- **Per task commit:** `python -m pytest tests/test_skill_loaded_notification.py -x` (backend tasks) or `npm run typecheck` (TUI tasks)
- **Per wave merge:** `python -m pytest -q` && `npm run typecheck` && `npm run build`
- **Phase gate:** Full suite green before `/gsd-verify-work`; plan 16-03's human E2E checkpoint is blocking (mirrors Phase 11's 11-04-03)

### Wave 0 Gaps
- [ ] `tests/test_skill_loaded_notification.py` — covers all five ACT-06 automated dimensions above (uses the `_build_runtime` real-stack fixture pattern from `test_skills_e2e.py` and the temp `skills_root` fixture from `test_skills_load_rpc.py`)
- [ ] `tests/conftest.py` — no change needed (existing fixtures suffice; the `skills_root`/`store`/`runtime` fixtures live in the test files)
- [ ] Framework install — none (pytest + asyncio_mode already configured)

## Security Domain

> `security_enforcement` is enabled (config.json key absent).

### Applicable ASVS Categories

| ASVS Category | Applies | Standard Control |
|---------------|---------|-----------------|
| V2 Authentication | no | Local single-user TUI over stdio; no auth surface |
| V3 Session Management | no | Sessions are local file-based; no web session |
| V4 Access Control | no | No multi-user or privileged operations added |
| V5 Input Validation | yes | `/skill` name passed raw to backend; backend validates (adapter.py:101 — INVALID_PARAMS for missing/non-str/empty, SKILL_NOT_FOUND for unknown, D-11 cap message for refusal). TUI does no normalization (12-CONTEXT D-06 matching is backend-side) |
| V6 Cryptography | no | No secrets, no encryption added |

### Known Threat Patterns for the notification pipeline

| Pattern | STRIDE | Standard Mitigation |
|---------|--------|---------------------|
| **Skill-name ANSI/control-char injection into the chip** | Tampering / Spoofing | Skill names come from author-controlled `SKILL.md` frontmatter (validated in Phase 12 — lenient name validation + win32 case handling); the chip renders the canonical name from the backend, which is the same value already echoed in the system-prompt manifest. The RPC channel is the TUI's own subprocess over pipes (no remote input). Risk is LOW and pre-existing — same trust boundary as every other notification payload the TUI renders (e.g. `tool_call` arguments in the tool monitor). No new mitigation required; do NOT render arbitrary user input into the chip beyond the canonical name. |
| **Event spoofing via duplicate `skill_loaded`** | Spoofing | The chip only ever appends (dedup-append in store); a forged duplicate shows the same skill once. Backend emits only on real loads (D-07). |
| **Notification/response ordering spoofing** | Tampering | The TUI treats notification and RPC response as independent channels (verified `handleMessage` routes by `id` presence vs `method:"event"`); the chip never depends on the ack, the notice never depends on the notification — no state can be corrupted by reordering. |

## Sources

### Primary (HIGH confidence — verified directly against the codebase on 2026-08-03)
- `harness/events.py` — full file: HarnessEvent base, 7 event dataclasses, EVENT_* constants (name == class name convention)
- `harness/runtime.py` — `load_skill` (178-213) and `load_skill_status` (215-232): exact dedup/refusal/injection points; `event_bus` property (163-165)
- `harness/event_bus.py` — `publish` is async, routes on `type(event).__name__`, handler isolation via gather(return_exceptions=True)
- `harness/__init__.py` — export pattern; new event/constant should join `__all__` for consistency
- `backend/rpc/protocol.py` — `NotificationType` enum (78-87), `RPC_METHODS` with `skills.load` (101), `SKILL_NOT_FOUND` (56)
- `backend/rpc/server.py` — `_DOMAIN_TO_NOTIFICATION` (53-61), `_PAYLOAD_EXTRACTORS` (115-123), `start()`/`shutdown()` subscribe/unsubscribe (161-183), `_event_to_notification` (202-233)
- `backend/rpc/adapter.py` — `handle_skills_load` (99-111): INVALID_PARAMS/SKILL_NOT_FOUND/INTERNAL_ERROR mapping
- `backend/rpc/dispatcher.py` — RPCError passthrough (72-78), INTERNAL_ERROR wrap (79-86)
- `tui-ink/src/bridge/rpc-client.ts` — `loadSkill()` (140-142), `handleMessage` routing (169-197), `handleEvent` switch (199-282)
- `tui-ink/src/types.ts` — `SkillLoadResult` (11-14), `EventPayload` union (67-74), `Message` (88-95), `AgentState` (97-109)
- `tui-ink/src/store/agent-store.ts` — `addNotice` (170-176), `addError` sets `status:"error"` (178-185), `resetConversation` (197-204), `loadConversation` (206-218), `setActiveSession` (60)
- `tui-ink/src/app.tsx` — InputBar `useInput` intercept (41-79), `/new`/`/session`/`/sessions` branches
- `tui-ink/src/components/footer.tsx`, `message.tsx`, `header.tsx` (error→red mapping), `session-picker.tsx` (`useWindowSize`, `loadConversation` call at 65), `conversation-panel.tsx` (MessageCard mapping)
- `skills/provider.py` — `read_skill` → `load_handler` → shared `load_skill` (49-55)
- `context/context.py` — `add_skill_message` (40-42), system-role/persist=False
- `main.py` — `run_rpc` (298-320), `--rpc` flag (325)
- `tests/` — `test_skills_load_rpc.py` (adapter/dispatcher patterns + `skills_root` fixture), `test_load_skill.py`, `test_skills_e2e.py` (`_build_runtime` real-stack pattern), `test_agent_events.py` (async collector pattern), `conftest.py` (StubAgent)
- `pytest.ini` — `asyncio_mode = auto`, `testpaths = tests`
- `tui-ink/package.json`, `tsconfig.json` — scripts (build/dev/start/typecheck only — **no test script**), strict TS
- Installed versions: ink 7.1.1, react 19.2.8, zustand 5.0.14, typescript 5.9.3 (node_modules), Python 3.12.5, pytest 8.4.2, Node v22.20.0 (runtime probes)
- `tui-ink/node_modules/ink/build/hooks/use-window-size.d.ts` — `{ columns, rows }` shape

### Secondary (MEDIUM confidence — verified against prior phase research)
- `.planning/phases/11-session-popup-and-panel-layout/11-RESEARCH.md` (lines 82, 117) — no TUI test infra; ink-testing-library v4.0.0 incompatible with Ink 5+/7 (input simulation unreliable) → typecheck + build + human E2E is the TUI verification bar
- `.planning/phases/11-session-popup-and-panel-layout/11-VALIDATION.md` — full suite command `python -m pytest -q && npm run typecheck && npm run build`; human E2E as blocking final-plan task (11-04-03)
- `.planning/phases/09-ts-tui-json-rpc/09-VERIFICATION.md` — notification pipeline verified by wiring inspection + human E2E (no automated server-level notification tests existed)

### Tertiary (LOW confidence — none used for critical claims)
- None — every load-bearing claim in this research is verified against live code or installed packages.

## Metadata

**Confidence breakdown:**
- Standard stack: **HIGH** — all versions confirmed from node_modules/registry; no new dependencies needed
- Architecture: **HIGH** — every touchpoint read directly; the extension checklist is mechanical
- Pitfalls: **HIGH** — each pitfall traces to a specific verified line (e.g. addError status flip, reset paths, order of wire writes)
- TUI test approach: **MEDIUM** — no TS test runner is the documented Phase 11 decision; if the milestone owner wants durable TUI regression tests, that is a follow-up decision (Assumptions Log A3)

**Research date:** 2026-08-03
**Valid until:** 2026-09-02 (stable stack; Ink/React/zustand/TS versions are current and pinned in package.json — no fast-moving risk)
