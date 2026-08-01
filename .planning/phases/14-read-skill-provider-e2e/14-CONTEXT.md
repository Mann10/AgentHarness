# Phase 14: read_skill Provider End-to-End - Context

**Gathered:** 2026-08-01
**Status:** Ready for planning

<domain>
## Phase Boundary

Agent can load a skill body on demand via a dedicated `read_skill` tool and read bundled resources through path-scoped reads — Level-2/Level-3 disclosure. Bodies flow through the persist-safe plumbing from Phase 13 as system-role messages. This phase delivers the backend read path end-to-end: SkillStore (index + load + traversal-guarded path reads), the `__skills__` tool provider, a single shared `RuntimeAPI.load_skill()` load path with body injection, and the cancel-mid-gather cleanup. The TUI indicator and `/skill` command are Phases 15/16.

</domain>

<decisions>
## Implementation Decisions

### read_skill tool surface
- **D-01:** Two tools, not one: `read_skill(name=...)` loads a skill body; `read_skill_path(skill=<name>, path=<rel>)` reads a bundled resource. Keeps each tool's schema and description clean.
- **D-02:** `read_skill` and `read_skill_path` are reserved, un-namespaced tool names registered by an async provider under the name `__skills__`. The LLM sees exactly `read_skill`/`read_skill_path` (no namespace prefix).
- **D-03:** A tool-name collision at registration (MCP server, builtin, or any provider already holding `read_skill`/`read_skill_path`) is rejected with a clear error. A skill can never shadow or be shadowed.
- **D-04:** `read_skill(name=...)` matches against the **frontmatter `name`** (the authoritative D-05 name) using the Phase 12 discovery index. Case-insensitive on win32, matching discovery (D-06).
- **D-05:** `read_skill` returns a **short ack** (e.g. `Loaded skill <name>`) — the body itself flows into context as a system-role message and is never duplicated in the tool result (ROADMAP success criterion 1).

### Body injection & load semantics
- **D-06:** The loaded skill body is appended at the **end** of the conversation messages as a system-role message (after prior user/assistant turns). It stays visible every turn; Phase 13's summarization exemption keeps it alive.
- **D-07:** Re-loading an already-loaded skill is a **no-op** — no duplicate body, returns an "already loaded" ack. Dedup is deterministic via `skill_state`.
- **D-08:** A dedicated `add_skill_message(name, body)` on the context marks the message `persist=False` and sets a `skill_name` attribute — Phase 13's persist filter skips it from JSONL, and Phase 16's TUI indicator detects skill messages by that tag.
- **D-09:** `load_skill()` (the single shared load path) writes `skill_state["loaded"]` as a deduped list of loaded skill names plus each skill's base dir. This is the shared record read_skill and the Phase 15 `/skill` command both use; Phase 17's filtering reads it.

### Path-scoping strictness
- **D-10:** `read_skill_path` reads **only inside the loaded skill's directory**. Reads into unloaded skills or anywhere outside are rejected.
- **D-11:** Symlinks are resolved (canonicalized) and containment is checked against the skill's real path. A symlink resolving outside the skill dir is rejected — no TOCTOU window, no escape (DISC-04).
- **D-12:** Rejected traversal returns a **clear error naming the skill and the rejected path** — never a silent empty result. The agent learns exactly what was refused. Tests cover `../`, `..\`, absolute paths, and win32 drive-path vectors (shipped in the same wave as the tool).

### Auto-invoke & cancel-mid-gather
- **D-13:** ACT-02 "auto-invoke" is **model-driven only** — the manifest + `read_skill` tool let the model decide; no keyword matching, no heuristic pre-loading (consistent with Milestone D-06 pure-LLM-reasoning). "Exactly once" is satisfied by D-07 dedup.
- **D-14:** The cancel-mid-gather hole is fixed this phase: cancelling a turn during the tool-result gather (agent/core.py) leaves **no partial tool messages and no dangling tool_calls** for the next turn. Verified with a regression test.
- **D-15:** End-to-end verification is **backend-only** (no TUI): load → inject → summarize-survive → JSONL untouched, all in Python tests. Phase 16 owns the TUI indicator; Phase 15 owns `/skill`.

### OpenCode's Discretion
- Exact ack wording for `read_skill`/`read_skill_path` results and error strings
- `read_skill_path` input schema details (beyond the `skill` + `path` contract)
- `skill_state["loaded"]` exact record shape (list of names + dirs is required; exact dict layout is open)
- Provider/Store caching granularity and thread-safety details
- Cancel-mid-gather cleanup implementation approach (as long as no partial messages / dangling tool_calls)

</decisions>

<canonical_refs>
## Canonical References

**Downstream agents MUST read these before planning or implementing.**

### Milestone & requirements (authoritative scope)
- `.planning/MILESTONE-CONTEXT.md` — Decisions D-08/D-09/D-10/D-12/D-13/D-15 define the read_skill activation model, path-scoped reads, bundled resources, session persistence, and script-not-tool rule
- `.planning/REQUIREMENTS.md` — DISC-03, DISC-04, DISC-05, ACT-02, CAP-01, CAP-03 — the six requirements this phase delivers

### Prior phase context (locked decisions)
- `.planning/phases/13-context-plumbing-persist-fix/13-01-PLAN.md` — `Message.persist` contract (default True, from_dict compat)
- `.planning/phases/13-context-plumbing-persist-fix/13-02-PLAN.md` — `to_events()` persist filter + identity-based save watermark
- `.planning/phases/13-context-plumbing-persist-fix/13-03-PLAN.md` — `skill_state` non-serialized field + system-role summarization exemption
- `.planning/phases/12-skills-discovery-manifest/12-CONTEXT.md` — discovery index, frontmatter-name authority (D-05), win32 case-insensitivity (D-06)

### Claude Code / Agent Skills model (external — research grounding)
- https://platform.claude.com/docs/en/agents-and-tools/agent-skills/overview — Three-level progressive disclosure (frontmatter always / SKILL.md on trigger / references on demand)
- https://code.claude.com/docs/en/skills — Custom skills: locations, invocation control, session persistence, allowed-tools

</canonical_refs>

<code_context>
## Existing Code Insights

### Reusable Assets
- `skills/discovery.py` `discover_skills()` / `parse_skill_entry()` — existing, tested one-pass discovery returning `SkillInfo` (name, description, path, allowed_tools). `read_skill` name lookup and the SkillStore index build on this.
- `skills/models.py` `SkillInfo` — already carries `name` (frontmatter-authoritative) and `path` (the skill dir); the base dir `read_skill_path` needs is right here.
- `tool/registry.py` — provider-based registry; `add_provider()`/`start()` register tools; collision detection exists in `_register_tools` (extend for the reserved-name rejection). `list_tools()` feeds the per-iteration LLM tool list.
- `tool/local_provider.py` — local provider pattern (start/fetch_tools/call_tool). The skill provider follows this shape but async.
- `session/models.py:47` `skill_state` dict — non-serialized field (Phase 13) ready to hold `loaded` names + dirs.
- `context/context.py` `add_message()` — Message + ConversationContext; a new `add_skill_message()` extends it with `persist=False` + `skill_name` tag.
- `harness/runtime.py` — `RuntimeAPI` is where the single shared `load_skill()` path lives; `_create_agent` rebuilds Agent per session.

### Established Patterns
- Dataclass models + explicit `__all__` barrel exports per package; absolute imports from project root (CONVENTIONS.md)
- Skip-and-warn error handling: corrupt data logged + skipped, never crashes the harness (session/store.py corrupt-JSONL pattern)
- `persist-flag` convention (Phase 13): datum-level boolean opt-out, defaults to persist — `add_skill_message` uses `persist=False`
- Non-serialized session-scoped state (Phase 13): dataclass fields omitted from `to_snapshot_meta()` never reach JSONL — `skill_state` is this pattern
- Provider pattern: `ToolProvider` interface (start/shutdown/fetch_tools/call_tool) implemented by local + MCP providers

### Integration Points
- `tool/registry.py` — `add_provider("__skills__", skill_provider, namespace=None)` registers the un-namespaced tools; `_register_tools` collision path enforces D-03
- `harness/runtime.py` — `load_skill(name)` single shared load path: discovery lookup → `add_skill_message` injection → `skill_state` update; consumed by the provider's read_skill handler
- `context/context.py` — new `add_skill_message(name, body)` (system role, persist=False, skill_name tag)
- `session/models.py` — `skill_state` reads/writes
- `agent/core.py` — tool-result gather path (cancel-mid-gather cleanup, D-14)
- `main.py` — skill provider registration wiring (registry assembly)

</code_context>

<specifics>
## Specific Ideas

- Modeled directly on Claude Code Agent Skills progressive disclosure: manifest → SKILL.md on trigger → references on demand (Milestone specifics)
- "I need it for my .agentharness (required)" — skills are project-local under the existing `.agentharness/` data dir
- "skill similar like claude codes skill with progressive disclosure" — load model: manifest in system prompt (cheap), body on tool-call (when relevant), resources on demand (during execution)

</specifics>

<deferred>
## Deferred Ideas

- **TUI "Skill loaded" indicator** — Phase 16 (the `skill_name` message tag from D-08 is the seam)
- **`/skill <name>` slash command + RPC** — Phase 15 (consumes the same `load_skill()` path)
- **allowed-tools enforcement + intersection semantics** — Phase 17 (reads `skill_state`; CAP-03 retention contract is unit-tested here per ROADMAP)
- **Script-as-tool registration** (skills bundle scripts that become first-class tools) — D-15 defers
- **User-global skills dir** (`~/.config/agentharness/skills/`) — D-01 defers
- **Skill chaining / nested skills** — future milestone
- **Keyword pre-matching for auto-invoke** — rejected this phase (D-13); milestone stays pure-LLM-reasoning

</deferred>

---

*Phase: 14-read-skill-provider-e2e*
*Context gathered: 2026-08-01*
