# AgentHarness

**Vision:** Terminal-based interactive agent harness that connects LLMs to tools via a REPL loop. Users chat with an AI agent that can use MCP-provided and built-in tools to accomplish tasks.

## What This Is

A terminal-first AI agent harness. Users chat with an LLM agent that can use MCP and built-in tools, in either a Python REPL or a rich Ink-based terminal UI (tui-ink/). The TUI streams tokens live, persists sessions as JSONL, supports session switching via a `/session` picker and fresh starts via `/new`, and shows a live date/time panel. Backend orchestration runs through a RuntimeAPI (EventBus, Scheduler, SessionManager, Agent) exposed to the TUI over a JSON-RPC stdio channel (`main.py --rpc`). Since v1.1, users can author Claude-Code-style skills (`.agentharness/skills/<name>/SKILL.md`) that surface to the agent as a budgeted manifest and load on demand via `read_skill` or `/skill`.

## Core Value

A reliable, session-persistent terminal chat loop where the LLM agent drives tools — with a TUI that makes long conversations fast to navigate and continue. Skills extend this: users encode reusable workflows the agent loads only when relevant.

## Current Milestone: v1.1 Skills System (SHIPPED 2026-08-04)

**Goal:** Progressive-disclosure skills — SKILL.md files under `.agentharness/skills/`, surfaced to the agent as a cheap manifest and loaded on demand.

**Progress:** SHIPPED. Phases 12-16 complete (20 plans), Phase 17 cancelled (allowed-tools enforcement deferred). Skills are live end-to-end: discovery + budgeted manifest in the system prompt (12), persist-safe session plumbing — bodies survive summarization but never hit JSONL (13), `read_skill` with traversal guard + single shared load path with exactly-once dedup (14), `/skill` command via 4-layer RPC + `LOADED_SKILL_TOKEN_CAP` (15), TUI `/skill` + "Skill loaded" indicator (16). 192 tests green. See `.planning/milestones/v1.1-ROADMAP.md`.

## Principles

- **Terminal-first** — CLI REPL + Ink TUI, no web UI
- **Provider-pluggable** — Tools come from MCP servers or local providers via a registry
- **Session-persistent** — Conversations survive restarts via JSONL storage
- **Python 3.12+** — Modern Python, async throughout

## Non-negotiable

- All LLM communication goes through OpenAI-compatible API (configurable base URL)
- Session data stored as JSONL in `.agentharness/`
- OpenAI `AsyncOpenAI` SDK for LLM calls

## Requirements

### Validated

- ✓ Core harness: LLM ↔ tool interaction loop with OpenAI-compatible client, tool registry, REPL — v1.0
- ✓ Session module: create/resume/list/switch conversations with JSONL persistence — v1.0
- ✓ Harness Runtime: RuntimeAPI orchestrator (EventBus, Scheduler, SessionManager, Agent) — v1.0
- ✓ Rich Textual TUI → replaced by Ink TUI in v1.0 (09/10/11)
- ✓ Token streaming: live chunk-by-chunk output with truncation on cancel — v1.0
- ✓ Session popup + panel layout: conversation-first layout, `/session` picker, `/new`, date/time panel — v1.0
- ✓ Auto-titled sessions shown in panel/header/date-panel on first question — v1.0 (quick task 260801-jra)
- ✓ Skills discovery + manifest: SKILL.md authoring, skip-and-warn discovery, budgeted `# Available Skills` in system prompt — v1.1
- ✓ Session-scoped skill persistence: loaded bodies survive summarization, never serialize to JSONL — v1.1
- ✓ `read_skill` end-to-end: traversal-guarded path-scoped reads, reserved `__skills__` provider, exactly-once dedup — v1.1
- ✓ `/skill` command: 4-layer RPC + REPL + TUI input-bar intercept, loaded-skill token cap — v1.1
- ✓ TUI skill indicator: typed `skill_loaded` notification, footer chip + notices — v1.1

### Active

- [ ] **AUTH-01**: User can create, list, and edit skills from the harness (management tools)
- [ ] **AUTH-02**: TUI shows a `/skills` listing command
- [ ] **EXPD-01**: Skills bundle scripts that register as first-class harness tools (script-as-tool)
- [ ] **EXPD-02**: Skills live in a user-global directory (~/.config/agentharness/skills/) for cross-project reuse
- [ ] **EXPD-03**: Skill chaining / nested skills
- [ ] **CAP-02**: `allowed-tools` filters the tool list passed to the LLM while a skill is loaded (deferred from v1.1 Phase 17; `skills/filter.py` contracts ready)
- [ ] **CAP-04**: Multi-skill `allowed-tools` intersection enforcement (semantics decided + unit-tested, un-wired)
- [ ] Tool system hardening (remove_provider, health-check, reconnect)
- [ ] Multi-turn agent improvements
- [ ] Package restructuring

### Out of Scope

- Web UI — terminal-first principle
- Non-OpenAI-compatible providers — non-negotiable constraint
- Skill authoring UI / management tools — deferred to future milestone (AUTH-01/02)
- User-global skills dir (~/.config/agentharness/skills/) — deferred to future milestone (EXPD-02)
- Script-as-tool registration — deferred (skills are markdown + bundled files in v1.1; EXPD-01)
- Keyword/algorithmic skill matching — progressive disclosure uses pure LLM reasoning over descriptions
- Persisting loaded skill bodies to JSONL — loaded skills are session-scoped (D-13)
- Loading all skill bodies at startup — defeats progressive disclosure

## Context

Shipped v1.0 (2026-08-01) and v1.1 Skills System (2026-08-04). Python async backend + Ink/React TUI. 192 pytest tests green (+1 skipped), TypeScript typecheck + build clean. The TUI communicates with the backend exclusively over JSON-RPC stdio (RPC_METHODS whitelist in backend/rpc/protocol.py). v1.1 added the skills stack: `skills/` package (discovery, manifest, limits, filter), `read_skill`/`read_skill_path` tools, `/skill` command, `skill_loaded` TUI notification. Known deferred items at v1.1 close: CAP-02/CAP-04 allowed-tools enforcement (Phase 17 cancelled) — see STATE.md; pre-existing WR-01/WR-02/WR-06/IN-02..IN-05 review residuals deferred to hardening.

## Key Decisions

| Decision | Outcome |
|----------|---------|
| RuntimeAPI as central orchestrator (D-05/05-05) | ✓ Good — single lifecycle for REPL/TUI/worker modes |
| TUI is a pure view layer over EventBus | ✓ Good — replaced by JSON-RPC stdio channel (Phase 09) |
| JSON-RPC stdio for TUI↔backend (Phase 09) | ✓ Good — typed client, event notifications, 9 methods |
| Auto-title sessions from first prompt (D-13) | ✓ Good — title persists synchronously in submit_prompt |
| /session full-screen picker, /new fresh start (D-11/D-12) | ✓ Good — keyboard-first, switch-only |
| Conversation-first layout with DatePanel (D-01/D-02) | ✓ Good — SessionPanel removed |
| Live clock via useEffect + setInterval in DatePanel | ✓ Good — 1 Hz tick isolated from streaming subtree |
| sessions.active RPC binding active session on TUI connect | ✓ Good — fixes "No session"/"untitled" on cold start |
| Budgeted manifest in system prompt (D-06/D-07, Phase 12) | ✓ Good — progressive disclosure, ~1,500-char cap |
| Loaded skills session-scoped, never to JSONL (D-13, Phase 13) | ✓ Good — persist filter + non-serialized skill_state |
| Single shared `load_skill()` path (Phase 14) | ✓ Good — read_skill + /skill cannot drift; exactly-once dedup |
| `allowed-tools` contract-before-enforcement (Phase 15) | ✓ Good as contract — pure functions unit-tested; enforcement deferred |
| Phase 17 allowed-tools enforcement CANCELLED (2026-08-04) | ⚠ Revisit — CAP-02/CAP-04 deferred to future/end milestone |
| `LOADED_SKILL_TOKEN_CAP` separate accounting (Phase 15) | ✓ Good — summarization threshold stays chat-relative |
| Typed `skill_loaded` notification, live-events-only chip (Phase 16) | ✓ Good — indicator never pollutes the message stream |

## Evolution

This document evolves at phase transitions and milestone boundaries.

**After each phase transition** (via `/gsd-transition`):
1. Requirements invalidated? → Move to Out of Scope with reason
2. Requirements validated? → Move to Validated with phase reference
3. New requirements emerged? → Add to Active
4. Decisions to log? → Add to Key Decisions
5. "What This Is" still accurate? → Update if drifted

**After each milestone** (via `/gsd-complete-milestone`):
1. Full review of all sections
2. Core Value check — still the right priority?
3. Audit Out of Scope — reasons still valid?
4. Update Context with current state

---
*Last updated: 2026-08-04 after v1.1 Skills System milestone*
