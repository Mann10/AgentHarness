# Phase 1: Core Harness - Context

**Gathered:** 2026-07-25 (retrospective from codebase map)
**Status:** Complete

<domain>
## Phase Boundary

Build the core REPL-based agent harness: LLM client, tool registry, local/MCP providers, and the agent orchestration loop.

</domain>

<decisions>
## Implementation Decisions

### Architecture
- **D-01:** Top-down orchestration — `main.py` sets up deps and injects into `Agent`
- **D-02:** Protocol-based tool plugins — `ToolProvider` is a `@runtime_checkable Protocol`
- **D-03:** Abstract base classes for LLM — `BaseLLMClient` defines the contract

### LLM Client
- **D-04:** OpenAI-compatible API via `AsyncOpenAI` SDK
- **D-05:** Configurable `base_url`, `model`, `api_key` via `.env`

### Tool System
- **D-06:** Tools from MCP servers (stdio/HTTP SSE) and local Python providers
- **D-07:** `ToolRegistry` manages provider registration and tool resolution
- **D-08:** Built-in file tools: `read_file`, `write_file`, `list_dir`
</decisions>

---

*Phase: 01-core-harness*
*Context gathered: 2026-07-25*
