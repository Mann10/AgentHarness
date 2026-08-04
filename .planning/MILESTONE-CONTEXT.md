# Milestone: Skills System (v1.1) - Context

**Gathered:** 2026-08-01
**Status:** Ready for new-milestone roadmap
**Branch:** `feature/skills-system`

<domain>
## Milestone Boundary

Build a Skills system for AgentHarness, modeled on Claude Code Agent Skills with progressive disclosure. Users author `SKILL.md` files under `.agentharness/skills/`; the harness surfaces each skill's `name` + `description` to the agent cheaply (manifest in the system prompt), and the full instruction body loads into context only when the agent (or user) decides the skill is relevant. This milestone is the discovery → activation → execution pipeline, not a skill-authoring UI.

Skill authoring (creation tools, management commands), skill marketplaces/sharing, and script-as-tool registration are separate milestones.
</domain>

<decisions>
## Implementation Decisions

### Skill storage & format
- **D-01:** Skills are project-local: `.agentharness/skills/<name>/SKILL.md`. Co-located with session/queue data (`.agentharness/`), versioned in repo. No user-global skill dir in this milestone.
- **D-02:** Folder per skill, kebab-case, `name` = folder name. Directory is `skills/<name>/` containing `SKILL.md` plus optional sibling `references/`, `scripts/`, `assets/`.
- **D-03:** Frontmatter: `name` + `description` are required. `allowed-tools` is an optional field used only when a skill needs tool sandboxing. `description` must be trigger-aware — it says what the skill does AND when to use it (this is the routing signal).
- **D-04:** Malformed skills (missing/invalid frontmatter) → log warning + skip. A broken skill never breaks the harness.
- **D-05:** Duplicate skill names → first-wins (deterministic sort order) + warning logs the shadowed skill.

### Progressive disclosure mechanism
- **D-06:** Discovery = manifest of every skill's `name` + `description` injected into the system prompt each turn (matches Claude Code — pure LLM reasoning over descriptions, no keyword matching).
- **D-07:** Manifest is subject to a token/cap budget (Claude Code uses ~1,500 chars for the skill listing). Skills over the cap are trimmed from the manifest — encourages concise descriptions.
- **D-08:** Activation = agent calls a dedicated `read_skill(name=...)` tool when the manifest description matches the current task. The tool returns the `SKILL.md` body + base-dir path. Path-scoped to `skills/` — no generic filesystem exposure.
- **D-09:** Bundled resources supported (`references/`, `scripts/`, `assets/`). The `SKILL.md` body points at them by relative path; they load on demand (Level-3 disclosure).
- **D-10:** `read_skill` exposes path-scoped reads into the skill directory so the agent can read sibling files (references/scripts) by path. Script code itself never enters context — only its output.

### Activation & session behavior
- **D-11:** Skills auto-invoke (model-driven) AND are user-invocable via a `/skill <name>` slash command added to the existing slash-command set (`/session`, `/new`, `/resume`).
- **D-12:** A loaded skill body persists for the session as a **system-role message**. `context/context.py:88` already excludes `role == "system"` from summarization — loaded skills survive compaction with no new mechanism. This matches Claude Code's "persists for session" and Claude's manifest always stays.
- **D-13:** Loaded skills are session-scoped, NOT persisted to the JSONL session file — lost on session close or `/new`.
- **D-14:** TUI shows a visible indicator when a skill loads (e.g. inline chip / status note "Skill loaded: <name>"). Transparency so users understand why agent behavior changed.

### Skill capabilities & scope
- **D-15:** Skill bodies are markdown instructions + bundled files. Bundled scripts are NOT registered as harness tools — the agent runs them via existing tools. `SKILL.md` remains the contract.
- **D-16:** `allowed-tools` (optional) is enforced by filtering the tool list passed to the LLM while the skill is loaded (session-scoped). Restrictions last as long as the skill is loaded.

### OpenCode's Discretion
- Exact manifest formatting/section heading in the system prompt
- Exact token budget number for the manifest cap
- `read_skill` tool schema details (input/output shape)
- TUI indicator widget style
- Where the skill-manifest assembly lives in `_build_system_prompt`

</decisions>

<specifics>
## Specific Ideas

- "I need it for my .agentharness (required)" — skills are project-local, live under the existing `.agentharness/` data dir.
- Modeled directly on Claude Code Agent Skills / the open Agent Skills standard (SKILL.md + frontmatter `name`/`description`, progressive disclosure: metadata → SKILL.md → references).
- User verified: summarization only affects chat messages, not the system prompt — manifest stays untouched; loaded skill bodies injected as system-role messages are automatically exempt (context.py:88).
- "skill similar like claude codes skill with progressive disclosure" — the load model should be: manifest in system prompt (cheap), body on tool-call (when relevant), resources on demand (during execution).

</specifics>

<canonical_refs>
## Canonical References

**Downstream agents MUST read these before planning or implementing.**

### Claude Code / Agent Skills model (external — research grounding)
- https://platform.claude.com/docs/en/agents-and-tools/agent-skills/overview — Three-level progressive disclosure (frontmatter always / SKILL.md on trigger / references on demand)
- https://code.claude.com/docs/en/skills — Custom skills in Claude Code: locations, invocation control, session persistence of loaded content, allowed-tools
- https://www.anthropic.com/engineering/equipping-agents-for-the-real-world-with-agent-skills — Design rationale for progressive disclosure

### AgentHarness integration points
- `session/models.py` §`_build_system_prompt` / §`to_llm_messages` — Where the skill manifest must be injected; system prompt is rebuilt per call, unaffected by summarization
- `context/context.py` §`_maybe_summarize` (esp. line 88 `if m.role != "system"`) — System-role exemption that lets loaded skills survive summarization
- `agent/core.py` §`run` / §`_stream_llm_call` — The tool loop where `read_skill` executes and where tool filtering applies; `registry.list_tools()` per iteration
- `tool/registry.py` §`list_tools` / §`call_tool` — Tool listing + dispatch; the `read_skill` tool registers here; allowed-tools filtering applies at the tool-list boundary
- `tui-ink/src` — Slash-command handling (`/session`, `/new`) and status indicators for the "Skill loaded" UI (Phase 11 patterns)

### Existing skill-file conventions (authoring reference)
- `.opencode/skills/graphify/SKILL.md` — Frontmatter `name`/`description` + body; the format AgentHarness skills should follow
- `.agents/skills/grilling/SKILL.md` — Minimal example; `name`/`description` only
- `.opencode/skills/gsd-discuss-phase/SKILL.md` — Skill that references external workflow docs via `@./path` includes

</canonical_refs>

<code_context>
## Existing Code Insights

### Reusable Assets
- `session/models.py` `Session._build_system_prompt()`: existing system-prompt assembler — the natural insertion point for the skill manifest (parts list pattern).
- `tool/registry.py`: provider-based tool registry with namespacing — the `read_skill` tool registers as a local provider; `list_tools()` already returns the per-iteration tool list that allowed-tools filtering would shape.
- `context/context.py` `Message` + `add_message()`: system-role messages already supported and summarization-exempt — skill body injection reuses this.
- `tool/config.py` / `tool/local_provider.py`: local tool provider pattern for a file-reading tool.
- TUI slash-command handling (Phase 11 `/session`, `/new`): pattern to extend with `/skill`.

### Established Patterns
- JSONL session storage under `.agentharness/` — skills dir mirrors this location convention.
- OpenAI-compatible tool-calling loop (`agent/core.py`): tools come from `registry.list_tools()` each iteration; a skill body can enter context as a message OR the loaded body can be attached as system content.
- Summarization exempts `system` role — using system-role for skill bodies gives free persistence.
- Phase 9 JSON-RPC contract pattern — if `/skill` needs backend coordination, it extends the RPC_METHODS whitelist (`backend/rpc/protocol.py`).

### Integration Points
- `session/models.py` `_build_system_prompt` — skill manifest assembly
- `tool/registry.py` — `read_skill` tool registration; allowed-tools filtering at `list_tools()`
- `agent/core.py` — tool-loop integration for load + filter
- `context/context.py` — skill body injection as system-role message
- `tui-ink/src` — `/skill` slash command + "Skill loaded" indicator
- `backend/rpc/protocol.py` — only if /skill requires backend RPC (else handled in agent loop)

</code_context>

<deferred>
## Deferred Ideas

- **Skill authoring / management tools** (create, list, edit skills from the harness) — future milestone
- **`/skills` listing command** (show available skills in TUI) — possible future phase or part of authoring milestone
- **Script-as-tool registration** (skills bundle scripts that become first-class registry tools) — D-15 explicitly defers this
- **User-global skills** (`~/.config/agentharness/skills/` personal skills across projects) — D-01 defers
- **Skill chaining / nested skills** — future milestone
- **Multiple simultaneous loaded skills + combined tool filtering** — edge case to handle in implementation, full support future
- **Manifest rebuild timing / frontmatter caching** — implementation detail, OpenCode discretion
- **Skill marketplace / sharing / plugin-provided skills** — future

</deferred>

---

*Milestone: v1.1 Skills System*
*Context gathered: 2026-08-01*
*Branch: feature/skills-system*
