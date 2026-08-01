# Feature Research

**Domain:** Progressive-disclosure agent skills system (SKILL.md + manifest + on-demand load)
**Researched:** 2026-08-01
**Confidence:** HIGH (ecosystem behaviors verified against agentskills.io open standard, Claude Code official docs, Anthropic engineering blog, and cross-agent comparisons)

## Feature Landscape

Categories used throughout: **Storage** (skill format & discovery on disk), **Disclosure** (how skills surface to the agent), **Activation** (how a skill gets loaded), **Capabilities** (what a loaded skill can do). Each row maps to the locked decisions D-01..D-16 from `.planning/MILESTONE-CONTEXT.md`.

### Table Stakes (Users Expect These)

The open Agent Skills standard (agentskills.io, adopted by Claude Code, Codex, Gemini CLI, Cursor, Microsoft Agent Framework, 30+ tools) defines three mandatory behaviors. Missing any of these = the system does not actually implement progressive disclosure.

| Feature | Why Expected | Complexity | Notes |
|---------|--------------|------------|-------|
| **SKILL.md format with required `name` + `description` frontmatter** (Storage) | The entire ecosystem standard is "folder per skill + SKILL.md + name/description frontmatter." Any author who has seen one agent's skills expects to drop the same file in this harness. | LOW | Locks D-01..D-03. One nuance: the standard requires `name` to **match the parent directory name** (lowercase, hyphens, 1–64 chars). Since D-02 says `name` = folder name, validate the frontmatter `name` matches the folder and warn on mismatch rather than failing. |
| **Manifest of name+description in the system prompt** (Disclosure) | Discovery-by-manifest is the canonical Level-1 disclosure. All conforming agents inject the skill catalog into the system prompt at session start (~50–100 tokens per skill). | LOW | Locks D-06. `_build_system_prompt()` in `session/models.py:63` is the insertion point. Free win: the system prompt is rebuilt on **every** `to_llm_messages()` call, so new/edited skills appear without a restart — no file-watcher needed (Claude Code needs live change detection; AgentHarness gets it for free). |
| **Description is the routing signal (says what AND when)** (Disclosure) | Standard-required: "The `description` is what Claude matches your request against... it must say both what the Skill does and when to use it." The agent triggers purely on LLM reasoning over descriptions — no keyword matching. | LOW | Locks D-03. Enforce at authoring-quality level only: log a warning for skills whose description is < ~20 chars (too vague to route on), don't reject. |
| **Manifest token/char budget with trimming** (Disclosure) | Claude Code truncates the combined skill listing at **1,536 characters**; the spec recommends a per-skill budget (~50–100 tokens each). A manifest without a cap is the #1 spec violation. | LOW | Locks D-07. Recommend Claude Code's char-based cap (1,536 chars for the combined listing) — simpler than token counting and matches user expectations. Deterministic trimming order (sort by name) so the manifest is stable turn-to-turn. |
| **On-demand activation: agent reads the full body when relevant** (Activation) | Level-2 disclosure — the full SKILL.md body loads only when the description matches the current task. Every conforming agent does this. | LOW | Locks D-08. Dedicated `read_skill(name=...)` tool is the standard's recommended "dedicated tool activation" pattern (Microsoft Agent Framework: `load_skill`; Claude Code: bash cat). Constrain the `name` param to a valid-skill-name enum in the tool schema to stop hallucinated skill names (agentskills.io client-implementation guidance). |
| **Loaded body persists for the session** (Activation) | Claude Code: "the rendered SKILL.md content enters the conversation as a single message and stays there for the rest of the session." Loaded skills must survive across turns. | LOW | Locks D-12. The system-role message approach reuses `context/context.py` `add_message()` — system role already supported. This is the cheapest correct implementation (see Differentiators: it's actually better than Claude Code's mechanism). |
| **User can invoke a skill directly** (Activation) | Every agent ships a direct invocation path: Claude Code `/skill-name`, Codex `$mention`, Codex `/skills` list. A skills system without user invocation forces users to phrase prompts to coax the model. | MEDIUM | Locks D-11, D-14. `/skill <name>` extends the `useInput` handler in `tui-ink/src/app.tsx` (existing `/session`, `/new` branches at lines 48–63). Needs backend coordination → new RPC method (`skills.load`) in `backend/rpc/protocol.py` `RPC_METHODS` whitelist. |
| **Malformed skill never breaks the harness** (Storage) | Standard ecosystems skip-and-warn on unparseable frontmatter. A broken skill crashing the loop would be immediately rejected by users. | LOW | Locks D-04. Scan+parse at session start; log warning; skip. Duplicate names → first-wins with deterministic sort + warning (D-05). |
| **Bundled resources load on demand (Level 3)** (Capabilities) | `references/`, `scripts/`, `assets/` — loaded only when the skill body points at them. "No practical limit on bundled content" is a selling point of the whole model. | LOW–MEDIUM | Locks D-09, D-10. Path-scoped reads into the skill dir via `read_skill(name, path=...)`. Must prevent `..` traversal (resolve + verify the joined path stays under the skill root). Script output enters context, script code never does (D-10). |

### Differentiators (Competitive Advantage)

These are places AgentHarness can be deliberately better than the reference implementations — not required, but they compound the Core Value (reliable, session-persistent terminal harness).

| Feature | Value Proposition | Complexity | Notes |
|---------|-------------------|------------|-------|
| **System-role summarization exemption = zero-machinery persistence** (Activation) | Claude Code needs a whole compaction re-attach subsystem: after auto-compaction it "re-attaches the most recent invocation of each skill after the summary, keeping the first 5,000 tokens of each" with a **25,000-token combined budget**, dropping older skills. AgentHarness gets strictly-better behavior for free: loaded skill bodies as `role == "system"` messages are exempt from summarization (`context/context.py:88`) and can't be dropped. No re-attach machinery, no budgets, no lossy behavior. | LOW | This is the highest-leverage architectural finding. D-12 is locked and correct. Flag to roadmap: summarization is a *requirement* for this design, not a risk — the system-role injection must be preserved through any future summarization refactor. |
| **`allowed-tools` as real enforcement (tool-list filtering)** (Capabilities) | The spec marks `allowed-tools` **experimental**; only Claude Code and Codex even parse it, and both treat it as a per-turn permission *grant* (pre-approval that "clears when you send your next message"), not a filter. Every other tool ignores it entirely. AgentHarness (D-16) enforces it as an actual **filter of the tool list while the skill is loaded** — stronger semantics than any reference implementation, and meaningful security value: a project skill can't drag the whole MCP surface into scope. | MEDIUM | Divergence to document in code: Claude Code's `allowed-tools` grants permissions; AgentHarness filters tools. For a harness with **no permission-prompt UX**, filtering is the only coherent interpretation — good call. Filter applies at `agent/core.py:108` `registry.list_tools()` per iteration. **Critical guardrail: `read_skill` itself must never be filtered out** while another skill is loaded, or the agent deadlocks (can't load references or another skill). |
| **Path-scoped `read_skill` (no generic filesystem exposure)** (Capabilities) | Claude Code reads skill files via generic bash/read (full filesystem access). AgentHarness confines Level-3 reads to the skill directory — smaller attack surface, predictable behavior, and testable in isolation. | LOW | Locks D-08/D-10. Path traversal guard is the only tricky part. This aligns with the harness's existing path-scoped philosophy (no MCP-permission prompts exist to fall back on). |
| **TUI "Skill loaded" transparency indicator** (Activation) | Users must understand *why* agent behavior changed. Claude Code shows loaded skills in context; a terminal harness with a tool-monitor panel can do better — an inline chip + the tool call `read_skill` appearing in `ToolMonitorPanel` gives users an honest audit trail. | LOW–MEDIUM | Locks D-14. Reuse the notice pattern (`addNotice` in `tui-ink/src/store/agent-store.ts` — existing `role: "notice"` messages) plus a dedicated `skill_loaded` event notification (new `NotificationType` + `EventPayload` union member in `tui-ink/src/types.ts`). |
| **Session-scoped, never persisted to JSONL** (Activation) | Clean session semantics: skills apply to the live session only; session files stay portable and replayable without the skills dir. Claude Code similarly keeps skills out of persisted session state but its compaction interaction complicates the story. | MEDIUM | Locks D-13. Implementation catch: `Session.to_events()` in `session/models.py:73` serializes **all** `_context._messages` — loaded skill bodies would leak into JSONL unless they're tracked separately from the persisted message list. Recommendation: keep a `loaded_skills` list on `Session` (not in `_context._messages`); inject bodies into the message stream only at `to_llm_messages()` assembly time, or mark them so `to_events()` skips them. `switch_session()` (`agent/core.py:59`) and `/new` must reset the loaded set. |
| **Manifest rebuilt per call = live skill discovery** (Disclosure) | Claude Code added a directory watcher for live skill changes. AgentHarness rebuilds `_build_system_prompt()` per LLM call, so a skill written mid-session appears in the manifest on the next turn with zero infrastructure. | LOW | Implement by scanning `.agentharness/skills/` inside `_build_system_prompt()`. Keep the scan cheap (stat + read only `SKILL.md`, cache frontmatter keyed by mtime). |

### Anti-Features (Commonly Requested, Often Problematic)

| Feature | Why Requested | Why Problematic | Alternative |
|---------|---------------|-----------------|-------------|
| **Keyword/embedding trigger matching** (Disclosure) | "More reliable than trusting the LLM." | The standard's design rationale (Anthropic engineering blog) explicitly rejects this: the agent reasons over descriptions because trigger logic changes per task; keyword matching is brittle, stale, and doesn't compose. Adds a whole matching subsystem. | Pure LLM reasoning over descriptions (D-06) — already locked. |
| **Script-as-tool registration** (Capabilities) | "Skills with scripts should expose them as first-class tools." | Adds registry/namespace complexity, tool-list bloat, and a new security surface (arbitrary local code as callable tools). The standard's design is that scripts execute via existing tools and only output enters context. | Locks D-15: scripts stay bundled files; agent runs them via existing tools. |
| **Persisting loaded skill bodies to JSONL** (Activation) | "Session resume should restore skills." | Bloat + staleness: session files grow, and a resumed session would replay bodies from a skill dir that may have changed. | Locks D-13: session-scoped only. |
| **Loading all skill bodies at session start** (Disclosure) | "Make sure the agent has everything." | Destroys the entire point of progressive disclosure — the context savings that make the feature valuable. | Manifest-only at start (D-06). |
| **Skill chaining / nested skills now** (Capabilities) | "Compose workflows." | Multi-skill tool-filter composition is a known hard edge case (deferred list in MILESTONE-CONTEXT). | Defer; single-loaded-skill enforcement first, document the composition rule when it lands. |
| **Authoring UI / marketplace now** (Storage) | "Make skills easy to create/share." | Authoring is editing a markdown file; a UI is a whole product. Marketplace adds trust/security requirements (the standard warns skills are executable instructions). | Deferred milestone (already listed in MILESTONE-CONTEXT deferred). |
| **User-global skills dir (`~/.config/...`)** (Storage) | "Personal skills across projects." | Precedence rules (personal vs project) add complexity; D-01 explicitly defers. | Deferred. |
| **Manifest without a cap** (Disclosure) | "Why truncate my descriptions?" | A manifest of full descriptions silently eats context every turn and defeats Level-1 disclosure. | Locks D-07: cap + trim, matching Claude Code's 1,536-char listing. |
| **`allowed-tools` as permission-grant (Claude Code semantics)** (Capabilities) | "Match Claude Code exactly." | AgentHarness has no permission-prompt UX, so a grant has nothing to grant against; it would be inert. Filtering (D-16) is the semantically-correct mapping. | Keep D-16 filter semantics; note the divergence in code docs. |

## Feature Dependencies

```
Skill discovery (scan .agentharness/skills/)
    └──requires──> Frontmatter parsing (name, description, allowed-tools)

Manifest assembly (D-06)
    └──requires──> Skill discovery
    └──requires──> Manifest budget + trim (D-07)

read_skill tool (D-08)
    └──requires──> Skill discovery (valid-name enum for schema)
    └──requires──> Path-scoped file reads (D-10)

Loaded-skill state (D-12, D-13)
    └──requires──> read_skill activation path AND /skill command path (shared loader)
    └──requires──> Session-scoped tracking (survives turns, dies on switch//new)

allowed-tools filter (D-16) ──enhances──> Loaded-skill state
    └──requires──> Tool-list boundary hook (agent/core.py:108)
    └──requires──> Guardrail: read_skill never filtered

/skill slash command (D-11) ──enhances──> Loaded-skill state
    └──requires──> RPC method (backend/rpc/protocol.py RPC_METHODS)
    └──requires──> TUI InputBar branch (tui-ink/src/app.tsx) + skill_loaded event

TUI indicator (D-14) ──enhances──> /skill command AND auto-activation

Summarization interaction (context.py:88) ──supports──> Loaded-skill state
```

### Dependency Notes

- **Manifest assembly requires discovery + budget:** the scan feeds `_build_system_prompt()`; the trim order must be deterministic (sort by name) so the manifest doesn't reorder turn-to-turn (D-05 first-wins also needs this sort).
- **Both activation paths share one loader:** `read_skill` tool call (agent-initiated) and `/skill` command (user-initiated) must funnel into the same "load body + track as loaded skill" function, or the two paths drift (one persists, one doesn't).
- **allowed-tools filter requires loaded-skill state, and the two must be coherent:** the filter applies *while the skill is loaded* (D-16), so unload on session switch/`/new` must clear the filter too, or tools stay hidden after the skill is gone. Same reset path.
- **read_skill never filtered:** if a skill's allowed-tools filter removes `read_skill`, the agent can't load references (D-10) or a second skill — a deadlock. `read_skill` must be whitelisted at the filter boundary unconditionally.
- **Summarization is an enabling dependency, not a risk:** the design only works because `context/context.py:88` exempts system-role messages. But note the side effect: loaded bodies add to `total_tokens` (context.py `add_message` increments), so large skill bodies push the conversation toward the summarization threshold sooner — intended (skills consume budget) but means the manifest cap and lean-body guidance matter. Claude Code solves the same pressure with its 25k re-attach budget; AgentHarness's system-role exemption handles it without machinery, at the cost of loaded bodies being *permanent* for the session. Acceptable for v1.1; document that a loaded body cannot be unloaded except via `/new`.
- **`/skill` command conflicts with the prompt pass-through:** `app.tsx` currently sends any non-matching input to `submitPrompt`. `/skill <name>` must be intercepted before that fallback (same pattern as `/session`, `/new`) and routed to the new RPC method — never sent as a chat prompt.

## MVP Definition

### Launch With (v1.1)

- [x] SKILL.md folder-per-skill discovery + frontmatter parse (D-01..D-04, D-05) — the format is the contract
- [x] Manifest in system prompt with char cap + trim (D-06, D-07) — Level-1 disclosure
- [x] `read_skill` tool: valid-name enum, body + base-dir return, path-scoped Level-3 reads (D-08, D-09, D-10) — Level-2/3 disclosure
- [x] Loaded-skill session state: system-role persistence, summarization-exempt, session-scoped, not persisted to JSONL (D-12, D-13)
- [x] `/skill <name>` slash command via RPC (D-11)
- [x] `allowed-tools` enforcement at the tool-list boundary + read_skill guardrail (D-16)
- [x] TUI "Skill loaded" indicator + `skill_loaded` event (D-14)

### Add After Validation (v1.x)

- [ ] `/skills` listing command in TUI (show available skills) — trigger: users can't remember skill names; deferred in MILESTONE-CONTEXT but a natural small follow-up
- [ ] Duplicate-name shadowing surfaced in TUI (not just logs) — trigger: user confusion when a skill silently loses a name collision
- [ ] Skill-body size warnings at author time (>500 lines or >5k tokens, the spec recommendation) — trigger: large skills causing premature summarization
- [ ] Frontmatter `name`≠folder validation warning — trigger: users copy skills between agents

### Future Consideration (v2+)

- [ ] Skill authoring/management commands (create, list, edit) — separate milestone, already deferred
- [ ] Skill marketplace / plugin-provided skills / user-global skills dir — trust + precedence complexity, deferred
- [ ] Script-as-tool registration — deferred by D-15
- [ ] Multiple simultaneous loaded skills + combined tool filtering — deferred; the single-skill filter logic should be written to compose
- [ ] Skill chaining / nested skills — deferred

## Feature Prioritization Matrix

| Feature | User Value | Implementation Cost | Priority |
|---------|------------|---------------------|----------|
| SKILL.md discovery + frontmatter parse (D-01..D-05) | HIGH | LOW | P1 |
| Manifest in system prompt + budget (D-06, D-07) | HIGH | LOW | P1 |
| `read_skill` tool + path-scoped reads (D-08..D-10) | HIGH | LOW–MEDIUM | P1 |
| Session-scoped loaded state + summarization-exempt persistence (D-12, D-13) | HIGH | MEDIUM | P1 |
| `/skill` slash command (D-11) | MEDIUM | MEDIUM | P1 |
| `allowed-tools` filtering (D-16) | MEDIUM | MEDIUM | P1 |
| TUI loaded-skill indicator (D-14) | MEDIUM | LOW–MEDIUM | P1 |
| `/skills` listing command | MEDIUM | LOW | P2 |
| Skill-body size warnings | LOW | LOW | P2 |
| name≠folder validation warning | LOW | LOW | P2 |
| Multi-skill composition | MEDIUM | HIGH | P3 |
| Authoring UI / marketplace | MEDIUM | HIGH | P3 |

**Priority key:** P1 = core progressive-disclosure loop, P2 = quality-of-life after core validated, P3 = deferred milestones.

## Competitor Feature Analysis

| Feature | Claude Code | Codex CLI | Gemini CLI | Microsoft Agent Framework | AgentHarness (planned) |
|---------|-------------|-----------|------------|---------------------------|------------------------|
| Skill location | `.claude/skills/` (project), `~/.claude/skills/` (personal) | `.agents/skills/` (repo), `~/.agents/skills/`, `/etc/codex/skills/` | `.gemini/skills/` + `.agents/skills/` (alias) | Configurable sources (file, MCP, code) | `.agentharness/skills/` (project-only, D-01) |
| Level-1 manifest | In system prompt, ~100 tokens/skill, 1,536-char listing cap | In system prompt (`render_skills_section`), name+description+path | In system prompt at session start | "Advertise" in system prompt | Manifest in system prompt, char cap (D-06/D-07) |
| Level-2 activation | Model runs `bash cat SKILL.md` (generic fs) | Model calls `read_file` (generic fs) | `activate_skill` tool **with consent prompt** | `load_skill` tool | Dedicated `read_skill` tool, path-scoped (D-08) |
| Level-3 resources | bash reads of bundled files | read_file | Via activate + read | `read_skill_resource`, `run_skill_script` (conditional advertisement) | `read_skill(name, path=...)` scoped to skill dir (D-10) |
| User invocation | `/skill-name` (name = dir name); merged commands | `$skill-name` mention, `/skills` list | By name in prompt | N/A (SDK) | `/skill <name>` (D-11) |
| Loaded-body persistence | Stays in conversation for session; re-attach (5k each, 25k combined) after compaction | Injected into conversation per turn | Injected on activation | Tool returns content | System-role message, summarization-exempt (D-12) — no re-attach machinery needed |
| Tool restriction | `allowed-tools` = per-turn permission **grant**; `disallowed-tools` = pool removal | Parses `allowed-tools` best-effort | Ignores `allowed-tools` | N/A | `allowed-tools` = **tool-list filter while loaded** (D-16) — stronger than all |
| Change detection | Directory watcher (live) | Rescan at session start | Session start | N/A | Per-call rebuild = free live discovery |
| Malformed skill | Skips with warning | Skips | Skips | N/A | Skips with warning (D-04) |
| Consent UX | Permission prompts (existing system) | `approval_policy` | **Consent prompt on activation** | N/A | None — filter semantics instead (no prompt UX in harness) |

## Interaction With Existing Session/Summarization Mechanics

This is the critical integration surface — the milestone's quality gate asked for it explicitly.

**What already works (no new code):**
- `context/context.py:88` `if m.role != "system"` — loaded skill bodies injected as system-role messages are summarization-exempt. Verified against the existing `_maybe_summarize()` logic.
- `context/context.py` `Message` + `add_message()` supports system role with token counting — reuse as-is for injection.

**What needs new code (dependencies on existing code):**
1. **Manifest assembly** → `session/models.py` `_build_system_prompt()` (parts-list pattern, line 63–69). Add a `# Skills` section. Rebuilt per call = free live discovery.
2. **read_skill tool** → register via `LocalToolProvider` pattern (`tool/local_provider.py`) + `ToolRegistry.add_provider()`; valid-name enum schema; returns body + base-dir; path-scoped reads with traversal guard. Async handler needed for path resolution + body read (handler signature in `local_provider.py` is currently sync `Callable[[dict], str]` — needs an async variant or a wrapper).
3. **allowed-tools filter** → apply at `agent/core.py:108` (`tools = self._registry.list_tools()` per iteration), driven by loaded-skill state; whitelist `read_skill`.
4. **Loaded-skill state** → new session-scoped tracking; **critical catch: `Session.to_events()` (`session/models.py:73`) serializes all `_context._messages`** — injected system-role bodies would persist to JSONL unless tracked separately (keep bodies in a `loaded_skills` collection, inject at `to_llm_messages()` assembly, or tag for `to_events()` exclusion). This is the one place D-12 (persist in session) and D-13 (not persisted to file) collide with existing code.
5. **`/skill` RPC** → extend `RPC_METHODS` whitelist (`backend/rpc/protocol.py:83`); shared loader function with the tool-call path.
6. **TUI** → new branch in `InputBar` `useInput` (`tui-ink/src/app.tsx:48–63`); new `skill_loaded` notification in `NotificationType` (`backend/rpc/protocol.py:70`) + `EventPayload` union (`tui-ink/src/types.ts`); indicator via existing notice pattern (`agent-store.ts` `addNotice`).
7. **Reset semantics** → `agent/core.py` `switch_session()` (line 59) and `/new` must clear loaded-skill state + filters.

**Frontmatter parsing dependency (flag):** `requirements.txt` has no YAML library. Options: (a) add `pyyaml` (safe for quoted descriptions, minimal cost) or (b) hand-roll a minimal frontmatter parser (frontmatter is a bounded YAML subset: `name`, `description`, `allowed-tools` — all scalars/lists). Recommend (a) pyyaml for correctness, or a small strict parser if avoiding the dependency matters. The agentskills.io client-implementation doc shows the minimal parsing shape (delimit `---`, parse block, strip before body).

## Sources

- **Agentskills.io open standard (specification + client-implementation guide)** — HIGH: three-tier disclosure, name/description requirements, ~50–100 token catalog cost, dedicated-tool activation pattern, conditional tool registration, `allowed-tools` experimental status. https://agentskills.io/specification , https://agentskills.io/client-implementation/adding-skills-support.md
- **Claude Code official docs (Extend Claude with skills)** — HIGH: location rules, session persistence of loaded content, 1,536-char listing cap, `allowed-tools` as per-turn grant, compaction re-attach (5k/skill, 25k combined), live change detection, invocation control. https://code.claude.com/docs/en/skills
- **Anthropic engineering blog — "Equipping agents for the real world with Agent Skills" (2025-10-16)** — HIGH: design rationale, progressive disclosure as the core principle, why description must be trigger-aware, why no keyword matching, script-execution-vs-context rationale. https://www.anthropic.com/engineering/equipping-agents-for-the-real-world-with-agent-skills
- **Anthropic platform docs — Agent Skills overview** — HIGH: three-level table (Level 1 metadata ~100 tokens / Level 2 instructions <5k / Level 3 resources), security guidance. https://platform.claude.com/docs/en/agents-and-tools/agent-skills/overview
- **Microsoft Agent Framework skills docs (2026-07)** — MEDIUM: `load_skill`/`read_skill_resource`/`run_skill_script` conditional advertisement — validates the dedicated-tool approach. https://learn.microsoft.com/en-us/agent-framework/agents/skills
- **Codex CLI implementation deep-dive (zenn, 2026-01)** — MEDIUM: `render_skills_section` manifest shape, `build_skill_injections` per-turn injection, no script auto-execution. https://zenn.dev/takiko/articles/codex-cli-agent-skills-implementation
- **Cross-agent portability analyses (MCP.Directory 2026-05, Codex Knowledge Base 2026-05)** — MEDIUM: adoption matrix (which agents parse SKILL.md natively, which ignore `allowed-tools`), `.agents/` path stabilization. https://mcp.directory/blog/cross-agent-skills-cursor-codex-cline-antigravity-gemini-mastra-portability
- **AgentHarness codebase (verified in-repo)** — HIGH: `session/models.py` (`_build_system_prompt`, `to_events`), `context/context.py:88` (summarization exemption), `agent/core.py:108` (tool-list boundary), `tool/registry.py`/`tool/local_provider.py` (tool registration), `backend/rpc/protocol.py` (RPC_METHODS), `tui-ink/src/app.tsx` (slash commands), `tui-ink/src/store/agent-store.ts` (notice pattern).
- **In-repo skill examples** — HIGH: `.opencode/skills/graphify/SKILL.md` (frontmatter + body convention the format should match).

---
*Feature research for: AgentHarness Skills System (v1.1)*
*Researched: 2026-08-01*
