# AgentHarness

**Vision:** Terminal-based interactive agent harness that connects LLMs to tools via a REPL loop. Users chat with an AI agent that can use MCP-provided and built-in tools to accomplish tasks.

## Principles

- **Terminal-first** — CLI REPL, no web UI
- **Provider-pluggable** — Tools come from MCP servers or local providers via a registry
- **Session-persistent** — Conversations survive restarts via JSONL storage
- **Python 3.12+** — Modern Python, async throughout

## Non-negotiable

- All LLM communication goes through OpenAI-compatible API (configurable base URL)
- Session data stored as JSONL in `.agentharness/`
- OpenAI `AsyncOpenAI` SDK for LLM calls
