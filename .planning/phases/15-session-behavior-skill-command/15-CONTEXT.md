# Phase 15: Session Behavior & /skill Command - Context

**Gathered:** 2026-08-02
**Status:** Ready for planning

<domain>
## Phase Boundary

Loaded-skill state becomes user-invocable and accounted: a `/skill <name>` slash command in the REPL loads skills through the same shared `load_skill()` path as `read_skill` (no drift between model-driven and user-driven activation), the new `skills.load` RPC method spans the full 4-layer contract (protocol.py → adapter.py → rpc-client.ts → types.ts) for the TUI to consume in Phase 16, loaded-skill tokens are accounted separately from chat tokens with a bounded cap, and the CAP-04 combined-filter semantics decision is locked here for Phase 17 to enforce. This phase covers backend + REPL + RPC contract only — the TUI indicator, `/skill` input-bar intercept, and `skill_loaded` notification are Phase 16; allowed-tools enforcement is Phase 17.

</domain>

<decisions>
## Implementation Decisions

### /skill command UX
- **D-01:** On success, `/skill <name>` prints a **short ack** only (`Loaded skill <name>`). The body already flowed to context as a system-role message; echoing it would duplicate it (mirrors read_skill's D-05 ack contract).
- **D-02:** Bad input yields **distinct errors + usage**, never a silent no-op or fall-through to a chat prompt (ROADMAP criterion 2): unknown name → `Skill '<name>' not found.`; no argument → a usage line.
- **D-03:** Loading an already-loaded skill is a **no-op** that matches read_skill's exactly-once dedup (14-CONTEXT D-07): `/skill demo-greeter` twice → second prints `Skill 'demo-greeter' already loaded`, body never re-injected.
- **D-04:** `/skill` name matching is **case-insensitive on win32**, consistent with discovery (12-CONTEXT D-06) and the canonical-name dedup from 14-05.

### RPC method & payload
- **D-05:** Expose a **single `skills.load` RPC method**, whitelisted in `RPC_METHODS` following the existing `sessions.*` namespacing pattern in `protocol.py`.
- **D-06:** Response is an **ack + status field**: `{ skill: <name>, status: loaded | already_loaded | not_found }`. No body echoed. Both REPL and TUI (Phase 16) render from this shape.
- **D-07:** **REPL calls `runtime.load_skill()` directly** (it is in-process with RuntimeAPI); the RPC method exists for the TUI/remote clients. Both share the exact same load path, so activation cannot drift.
- **D-08:** Skill-not-found over RPC uses **structured JSON-RPC error codes**: `-32602 INVALID_PARAMS` for a missing argument, a domain code (e.g. `-32001`) for skill-not-found, with a message string. Uses the existing `RPCError` shape.

### Loaded-skill token accounting & cap
- **D-09:** Loaded-skill tokens are **counted at load time** via `client.count_tokens()` (tiktoken, `llm/base.py`) and **cached per skill** in `skill_state`. Chat tokens stay separate, so the summarization threshold remains chat-relative (ROADMAP criterion 3).
- **D-10:** The cap is a **token cap on the combined loaded-skill bodies**, configurable via env var (mirrors the `SKILL_MANIFEST_MAX_CHARS` pattern from Phase 12, but tokens not chars since this bounds the context window).
- **D-11:** When loading would exceed the cap, **refuse with a clear error** naming the cap (`Skill '<name>' not loaded — loaded-skill token cap (N) would be exceeded`). No partial state, no silent drop, no auto-eviction.
- **D-12:** Default cap **~8k tokens** (env-var override). Generous for real skill docs (~500-2k tokens each), bounded enough to protect the window.

### CAP-04 combined-filter semantics (locked for Phase 17)
- **D-13:** Multiple loaded skills with `allowed-tools` filter by **intersection** — a tool is retained only if it is in EVERY loaded skill's `allowed-tools` list. `read_skill`/`read_skill_path` always retained (CAP-03). Locked now, enforced Phase 17.
- **D-14:** A loaded skill with **no `allowed-tools` field imposes no restriction** — treated as allowing everything; the intersection is computed over the restricted skills only.

### OpenCode's Discretion
- Exact usage-line wording and error string wording (beyond the given examples)
- Exact domain error code integer for skill-not-found (e.g. `-32001`)
- Env-var name for the loaded-skill token cap
- How the cached per-skill token count is stored in `skill_state` (the per-skill cache key/record shape)
- Whether `skills.load` is the method name on the TS side vs a wrapper in rpc-client.ts (as long as `protocol.py` RPC_METHODS has `skills.load`)

</decisions>

<canonical_refs>
## Canonical References

**Downstream agents MUST read these before planning or implementing.**

### Milestone & requirements (authoritative scope)
- `.planning/MILESTONE-CONTEXT.md` — Milestone decisions D-01..D-16; the `/skill` command, session behavior, and allowed-tools context for the v1.1 Skills System
- `.planning/REQUIREMENTS.md` §ACT-01, §CAP-04 — ACT-01 (`/skill` force-load) is this phase's requirement; CAP-04 intersection semantics decided here, enforced Phase 17

### Prior phase context (locked decisions)
- `.planning/phases/14-read-skill-provider-e2e/14-CONTEXT.md` — D-09 (`skill_state["loaded"]` shared record), D-07 (exactly-once dedup), D-05 (short ack), D-08 (`add_skill_message` + `skill_name` tag)
- `.planning/phases/14-read-skill-provider-e2e/14-05-SUMMARY.md` — canonical-name dedup implementation the `/skill` command inherits
- `.planning/phases/12-skills-discovery-manifest/12-CONTEXT.md` — D-06 win32 case-insensitivity, D-09/D-10 manifest cap pattern (chars), the discovery index `/skill` name lookup builds on

### RPC contract (4-layer)
- `backend/rpc/protocol.py` — `RPC_METHODS` whitelist, `RPCRequest`/`RPCResponse`/`RPCError` shapes, JSON-RPC error code constants
- `backend/rpc/adapter.py` — method → handler dispatch; `skills.load` handler lands here
- `tui-ink/src/bridge/rpc-client.ts` — TS RPC client the new method must be exposed through (Phase 16 consumer)
- `tui-ink/src/types.ts` — TS types for RPC methods/responses

### REPL integration
- `main.py` §`_handle_session_cmd` (lines 57-121) — the existing `/sessions`, `/new`, `/resume`, `/title` dispatch the `/skill` branch joins; §`run_repl` (124+) — REPL loop wiring

</canonical_refs>

<code_context>
## Existing Code Insights

### Reusable Assets
- `harness/runtime.py` `RuntimeAPI.load_skill()` — the single shared load path `/skill` consumes (already dedups against canonical name, mark-before-inject, writes `skill_state["loaded"]`)
- `session/models.py` `skill_state` — non-serialized dict (Phase 13) ready to hold the loaded names + dirs + per-skill cached token counts
- `llm/base.py` `count_tokens()` — tiktoken-based counting for the loaded-skill token accounting
- `main.py` `_handle_session_cmd()` — the existing slash-command dispatcher the `/skill` branch slots into; `run_repl` loop already returns early on handled commands
- `backend/rpc/protocol.py` — `RPC_METHODS` list + `RPCError`; adding `skills.load` follows the `sessions.*` pattern exactly
- `skills/discovery.py` `discover_skills()` — index `/skill` name lookup builds on (case-insensitive win32 match already handled)

### Established Patterns
- Slash-command dispatch: `_handle_session_cmd` returns `True` to signal "handled, don't fall through to chat" — `/skill` follows this
- Short ack results (14-CONTEXT D-05): tool/RPC results acknowledge without echoing body content
- Exactly-once dedup via `skill_state["loaded"]` (D-07 + 14-05 canonical-name fix)
- JSON-RPC structured errors: `RPCError` with code/message/data; whitelisted methods in `RPC_METHODS`
- Env-var configurable caps with defaults (`SKILL_MANIFEST_MAX_CHARS` pattern, Phase 12)

### Integration Points
- `main.py` `_handle_session_cmd` — add `/skill` branch (parse name, call `runtime.load_skill`, print ack/error/usage)
- `backend/rpc/protocol.py` — add `"skills.load"` to `RPC_METHODS`
- `backend/rpc/adapter.py` — map `skills.load` → `runtime.load_skill` with status/error mapping
- `tui-ink/src/bridge/rpc-client.ts` + `tui-ink/src/types.ts` — expose `skills.load` for Phase 16
- `harness/runtime.py` — loaded-skill token accounting hooks into `load_skill` (count + cache + cap check)
- `session/models.py` `skill_state` — per-skill cached token counts

</code_context>

<specifics>
## Specific Ideas

- `/skill` should feel exactly like the other slash commands (`/new`, `/resume`, `/title`) — local, immediate, consistent output style
- The `already loaded` ack wording matches what `read_skill` already returns — one dedup contract, two entry points
- Modeled on Claude Code's `/add`-style explicit loading: user-driven activation supplements the model-driven `read_skill` path rather than replacing it

</specifics>

<deferred>
## Deferred Ideas

- **TUI `/skill` input-bar intercept + "Skill loaded" indicator + `skill_loaded` notification** — Phase 16 (the `skills.load` RPC method from D-05/D-06 is its contract)
- **allowed-tools enforcement (per-iteration filter projection)** — Phase 17 (CAP-02; consumes `skill_state["loaded"]`, applies the D-13 intersection)
- **`/skills` listing command** (AUTH-02, v1.2) — deliberately not added to `/skill` in Phase 15; the no-argument `/skill` shows usage, not a listing
- **Auto-eviction of loaded skills at the cap** — rejected in D-11; cap breach refuses the load instead of silently dropping state the model may rely on

---

*Phase: 15-session-behavior-skill-command*
*Context gathered: 2026-08-02*
