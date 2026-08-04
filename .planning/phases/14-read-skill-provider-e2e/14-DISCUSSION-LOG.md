# Phase 14: read_skill Provider End-to-End - Discussion Log

> **Audit trail only.** Do not use as input to planning, research, or execution agents.
> Decisions are captured in CONTEXT.md — this log preserves the alternatives considered.

**Date:** 2026-08-01
**Phase:** 14-read-skill-provider-e2e
**Areas discussed:** read_skill tool surface, Body injection & load semantics, Path-scoping strictness, Auto-invoke & cancel-mid-gather

---

## read_skill tool surface

| Option | Description | Selected |
|--------|-------------|----------|
| Two tools: read_skill + read_skill_path | `read_skill(name=...)` returns the body; `read_skill_path(skill=<name>, path=<rel>)` reads bundled resources. Two clear, separately-scoped tools. | ✓ |
| One tool, optional path arg | Single `read_skill(name=...)` with optional `path` argument. Fewer tools but muddier schema. | |
| read_skill + generic read_resource | `read_skill(name)` loads body, generic `read_resource` handles all resource paths. Broader surface. | |

**User's choice:** Two tools: read_skill + read_skill_path
**Notes:** None

| Option | Description | Selected |
|--------|-------------|----------|
| Un-namespaced + collision rejection | `__skills__` provider registers un-namespaced so LLM sees exactly `read_skill`/`read_skill_path`; collision rejected at registration. | ✓ |
| Namespaced skills_read_skill | Registered under `skills` namespace; collision-safe but adds noise and breaks the roadmap's reserved-name contract. | |

**User's choice:** Un-namespaced + collision rejection
**Notes:** None

| Option | Description | Selected |
|--------|-------------|----------|
| Match on frontmatter name | Matches the authoritative D-05 name via Phase 12 discovery index; case-insensitive on win32. | ✓ |
| Match on folder name | Simpler but ignores frontmatter-authority and breaks on mismatches. | |

**User's choice:** Match on frontmatter name
**Notes:** None

| Option | Description | Selected |
|--------|-------------|----------|
| Short ack, body via context | Tool result = short ack; body flows into context as system-role message, never duplicated. | ✓ |
| Body in the result as well | Agent also sees body in tool result stream. Risks duplication. | |

**User's choice:** Short ack, body via context
**Notes:** None

---

## Body injection & load semantics

| Option | Description | Selected |
|--------|-------------|----------|
| Append at end of messages | System-role message appended after existing messages; visible every turn, summarization-exempt. | ✓ |
| Insert near system prompt | Body at front of message list. More prominent but reorders message flow. | |

**User's choice:** Append at end of messages
**Notes:** None

| Option | Description | Selected |
|--------|-------------|----------|
| Dedupe: no-op on re-load | Loading an already-loaded skill is a no-op, returns "already loaded" ack; dedup via skill_state. | ✓ |
| Re-inject every time | Every read_skill injects a fresh copy. Simpler but bloats context. | |

**User's choice:** Dedupe: no-op on re-load
**Notes:** None

| Option | Description | Selected |
|--------|-------------|----------|
| Tagged with skill_name | Dedicated `add_skill_message` marks persist=False + skill_name tag for JSONL skip + Phase 16 indicator. | ✓ |
| No tag, plain system message | No tag; Phase 16 would have to guess from content. | |

**User's choice:** Tagged with skill_name
**Notes:** None

| Option | Description | Selected |
|--------|-------------|----------|
| Record loaded names + dirs | `load_skill()` writes `skill_state["loaded"]` (deduped names + dirs); shared by read_skill and Phase 15 `/skill`. | ✓ |
| Don't write skill_state yet | Leave untouched; but then dedup has no home and Phases 15/17 have nothing to read. | |

**User's choice:** Record loaded names + dirs
**Notes:** None

---

## Path-scoping strictness

| Option | Description | Selected |
|--------|-------------|----------|
| Only the loaded skill's dir | `read_skill_path` reads only inside the loaded skill's directory. Strictest containment. | ✓ |
| Any skill under skills/ root | Reads any resource under skills/ even unloaded skills. More permissive. | |

**User's choice:** Only the loaded skill's dir
**Notes:** None

| Option | Description | Selected |
|--------|-------------|----------|
| Resolve + contain check, reject escape | Canonicalize + require containment in skill's real dir; symlink escaping rejected. | ✓ |
| Allow in-dir symlinks | Follow symlinks that resolve inside; TOCTOU and Windows-junction risk. | |

**User's choice:** Resolve + contain check, reject escape
**Notes:** None

| Option | Description | Selected |
|--------|-------------|----------|
| Clear error naming path | Reject with error naming skill + rejected path; tests cover `../`, `..\`, absolute, win32 drive vectors. | ✓ |
| Silent empty result | Simpler but hides refusals. | |

**User's choice:** Clear error naming path
**Notes:** None

---

## Auto-invoke & cancel-mid-gather

| Option | Description | Selected |
|--------|-------------|----------|
| Model-driven only, no matching | ACT-02 = model sees manifest + tool and decides; no keyword matching. "Exactly once" via dedup. | ✓ |
| Add keyword pre-matching | Heuristic auto-load before LLM call. Risks false positives, contradicts Milestone D-06. | |

**User's choice:** Model-driven only, no matching
**Notes:** None

| Option | Description | Selected |
|--------|-------------|----------|
| Partial-turn cleanup on cancel | Cancelled turn adds no partial tool messages, no dangling tool_calls; regression test. | ✓ |
| Defer the cancel fix | Document as known limitation; but ROADMAP lists it as a success criterion this phase. | |

**User's choice:** Partial-turn cleanup on cancel
**Notes:** None

| Option | Description | Selected |
|--------|-------------|----------|
| Backend E2E only | load → inject → summarize-survive → JSONL untouched, all Python. Phase 16 owns TUI, 15 owns /skill. | ✓ |
| Backend + TUI E2E | Spans TUI test infra and Phases 15/16 scope. | |

**User's choice:** Backend E2E only
**Notes:** None

---

## OpenCode's Discretion

- Exact ack wording for `read_skill`/`read_skill_path` results and error strings
- `read_skill_path` input schema details (beyond the `skill` + `path` contract)
- `skill_state["loaded"]` exact record shape (list of names + dirs required; exact dict layout open)
- Provider/Store caching granularity and thread-safety details
- Cancel-mid-gather cleanup implementation approach (as long as no partial messages / dangling tool_calls)

## Deferred Ideas

- TUI "Skill loaded" indicator — Phase 16
- `/skill <name>` slash command + RPC — Phase 15
- allowed-tools enforcement + intersection semantics — Phase 17 (CAP-03 retention contract unit-tested here)
- Keyword pre-matching for auto-invoke — rejected this phase (pure-LLM-reasoning preserved)
