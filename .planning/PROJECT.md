# AgentHarness

**Vision:** Terminal-based interactive agent harness that connects LLMs to tools via a REPL loop. Users chat with an AI agent that can use MCP-provided and built-in tools to accomplish tasks.

## What This Is

A terminal-first AI agent harness. Users chat with an LLM agent that can use MCP and built-in tools, in either a Python REPL or a rich Ink-based terminal UI (tui-ink/). The TUI streams tokens live, persists sessions as JSONL, supports session switching via a `/session` picker and fresh starts via `/new`, and shows a live date/time panel. Backend orchestration runs through a RuntimeAPI (EventBus, Scheduler, SessionManager, Agent) exposed to the TUI over a JSON-RPC stdio channel (`main.py --rpc`).

## Core Value

A reliable, session-persistent terminal chat loop where the LLM agent drives tools — with a TUI that makes long conversations fast to navigate and continue.

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

### Active

- [ ] Tool system hardening (remove_provider, health-check, reconnect)
- [ ] Multi-turn agent improvements
- [ ] Package restructuring

### Out of Scope

- Web UI — terminal-first principle
- Non-OpenAI-compatible providers — non-negotiable constraint

## Context

Shipped v1.0 (2026-08-01) with a Python async backend + Ink/React TUI. 63 pytest tests green, TypeScript typecheck + build clean. The TUI communicates with the backend exclusively over JSON-RPC stdio (RPC_METHODS whitelist in backend/rpc/protocol.py). Known deferred items at v1.0 close: a stale debug session (enter-not-submitting, resolving) and the Phase 09 verification gap — see STATE.md Deferred Items.

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

---
*Last updated: 2026-08-01 after v1.0 milestone*
