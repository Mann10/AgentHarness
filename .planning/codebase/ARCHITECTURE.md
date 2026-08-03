<!-- refreshed: 2026-07-25 -->
# Architecture

**Analysis Date:** 2026-07-25

## System Overview

```text
┌──────────────────────────────────────────────────────────────────┐
│                     Entry / CLI Layer                            │
│                        main.py                                   │
│           (REPL loop, session selection, /-commands)             │
└──────────┬────────────────────────────────────┬──────────────────┘
           │                                    │
           ▼                                    ▼
┌──────────────────────┐          ┌───────────────────────────────┐
│   Agent (agent/)     │          │  Session / Context Layer      │
│  `agent/core.py`     │          │  `session/`  `context/`       │
│  Orchestrates the    │◄────────►│  Manages messages, tokens,    │
│  LLM↔tools loop      │  uses    │  summarization, persistence   │
└───────┬──────────────┘          └───────────────────────────────┘
        │
        ├────────────────────┐
        ▼                    ▼
┌─────────────────┐  ┌──────────────────────┐
│  LLM Layer      │  │  Tool Layer          │
│  `llm/`         │  │  `tool/`             │
│  OpenAI client  │  │  Registry + Providers│
│  token counting │  │  MCP / Local         │
└─────────────────┘  └──────────────────────┘
```

## Component Responsibilities

| Component | Responsibility | File |
|-----------|----------------|------|
| **Config** | Loads env-var config via dataclass | `config.py` |
| **Agent** | Orchestrates LLM↔tool interaction loop | `agent/core.py` |
| **AgentResult** | Immutable result of a single `run()` | `agent/result.py` |
| **ConversationContext** | Message list, token tracking, auto-summarization | `context/context.py` |
| **Message** | Single conversation message (role, content, tool_calls) | `context/message.py` |
| **Session** | Full session state including context + metadata | `session/models.py` |
| **JSONLSessionStore** | Persists sessions to JSONL files | `session/store.py` |
| **BaseLLMClient** | Abstract LLM client interface | `llm/base.py` |
| **OpenAIClient** | OpenAI-compatible API client via `AsyncOpenAI` | `llm/openai_client.py` |
| **ToolRegistry** | Provider registry + tool name resolution | `tool/registry.py` |
| **LocalToolProvider** | Synchronous built-in tools (read/write/list) | `tool/local_provider.py` |
| **MCPToolProvider** | MCP protocol client (stdio/HTTP) | `tool/mcp_provider.py` |
| **MCPConfig / MCPServerConfig** | MCP server configuration dataclasses | `tool/config.py` |

## Pattern Overview

**Overall:** Modular layered architecture with plugin-style tool providers.

**Key Characteristics:**
- **Top-down orchestration**: `main.py` sets up dependencies and injects them into `Agent`, which owns the run loop
- **Protocol-based tool plugins**: `ToolProvider` is a `@runtime_checkable Protocol` — any object fulfilling the async interface is a provider
- **Session-persistent context**: Conversation state lives in `Session` → `ConversationContext`, persisted as JSONL files
- **Abstract base classes for LLM**: `BaseLLMClient` defines the contract; `OpenAIClient` is the single concrete implementation
- **Auto-summarization**: Context automatically summarizes older messages when approaching token limits

## Layers

**Entry / CLI Layer:**
- Purpose: Interactive REPL for user input, session management commands (`/sessions`, `/new`, `/resume`, `/title`)
- Location: `main.py`
- Contains: `async def main()`, `_resolve_session()`, `_handle_session_cmd()`, `_make_summarize_fn()`
- Depends on: `Agent`, `Config`, `OpenAIClient`, `JSONLSessionStore`, `ToolRegistry`, `LocalToolProvider`
- Used by: Direct invocation (`python main.py`)

**Agent / Orchestration Layer:**
- Purpose: Runs the LLM conversation loop — sends messages, processes tool call responses, iterates until text response
- Location: `agent/core.py`
- Contains: `class Agent` with `run()`, `start()`, `shutdown()`, `switch_session()`
- Depends on: `BaseLLMClient`, `ToolRegistry`, `Session`/`ConversationContext`
- Used by: `main.py`

**Context Layer:**
- Purpose: Manages message history, token counting, auto-summarization
- Location: `context/`
- Contains: `ConversationContext`, `Message`
- Depends on: `tool/models.py` (ToolCall), token counting callable
- Used by: `Agent`, `Session`

**Session Persistence Layer:**
- Purpose: Save/load conversation sessions as JSONL files; abstract store interface
- Location: `session/`
- Contains: `Session` (state+serialization), `SessionSummary`, `SessionStore` (ABC), `JSONLSessionStore`
- Depends on: `context/`
- Used by: `main.py`, `Agent` (minimally via context)

**LLM Layer:**
- Purpose: Unified interface to OpenAI-compatible LLM APIs
- Location: `llm/`
- Contains: `BaseLLMClient` (ABC), `OpenAIClient`, `LLMError`/`LLMConnectionError`/`LLMResponseError`
- Depends on: `config.py`, `tool/models.py` (Tool, LLMResponse), OpenAI SDK
- Used by: `Agent`

**Tool Layer:**
- Purpose: Tool registration, resolution, and execution via provider abstraction
- Location: `tool/`
- Contains: `ToolRegistry`, `LocalToolProvider`, `MCPToolProvider`, `ToolProvider` (protocol), `Tool`/`ToolCall`/`ToolResult` (dataclasses), `MCPConfig`/`MCPServerConfig`
- Depends on: `mcp` SDK, `tool/config.py`
- Used by: `Agent`, `main.py`

## Data Flow

### Primary Request Path

1. **User input** — `main.py` reads a line from stdin via `asyncio.to_thread(input(...))` (`main.py:197`)
2. **Session command check** — `_handle_session_cmd()` filters `/sessions`, `/new`, `/resume`, `/title` (`main.py:83`)
3. **Agent.run()** — `Agent.run(user_input)` is called (`main.py:209`)
4. **Add user message** — `ConversationContext.add_user_message()` stores the input (`agent/core.py:45`)
5. **LLM call** — `Session.to_llm_messages()` builds message list with system prompt + history, then calls `OpenAIClient.chat_from_messages()` (`agent/core.py:57-59`)
6. **Tool call detection** — If LLM returns `tool_calls`, they're dispatched concurrently via `asyncio.gather` through `ToolRegistry.call_tool()` (`agent/core.py:89-93`)
7. **Tool results fed back** — Each tool result is added to context via `add_tool_message()`, then loop resumes at step 5 (`agent/core.py:95-101`)
8. **Text response** — When LLM returns content without tool calls, result is returned to `main.py` (`agent/core.py:61-72`)
9. **Output** — `result.content` printed to stdout (`main.py:215`)
10. **Exit** — On `exit`/`quit` or EOF, session saved to JSONL via `JSONLSessionStore.save()` (`main.py:220-222`)

### Session Resume Flow

1. `_resolve_session()` lists saved sessions from `JSONLSessionStore.list_sessions()` (`main.py:37`)
2. User picks a session, calls `store.load(id)` (`main.py:69`)
3. `Session.from_events()` reconstructs session from JSONL events, stores them in `_stored_events` (`session/models.py:89-101`)
4. `session.restore_context()` rebuilds `ConversationContext` from stored events (`main.py:73-77`)
5. Agent switches to the session via `agent.switch_session()` (`main.py:141`)

**State Management:**
- **Session state**: Held in memory in `Session._context` (a `ConversationContext`). Persisted to `{session_id}.jsonl` files in `.agentharness/`.
- **Token tracking**: `ConversationContext.total_tokens` keeps running sum. Auto-summarization triggers at 75% of token limit.
- **Last-saved tracking**: `Session._last_saved_count` enables append-only persistence of new events.

## Key Abstractions

**ToolProvider (Protocol):**
- Purpose: Interface for any tool source — built-in functions, MCP servers, future providers
- Files: `tool/models.py:7-12`
- Pattern: `@runtime_checkable Protocol` with four async methods: `start()`, `shutdown()`, `fetch_tools()`, `call_tool()`

**SessionStore (ABC):**
- Purpose: Abstract persistence backend for sessions
- Files: `session/store.py:16-28`
- Pattern: ABC with four abstract methods: `save()`, `load()`, `delete()`, `list_sessions()`

**BaseLLMClient (ABC):**
- Purpose: Abstract interface for LLM backends
- Files: `llm/base.py:9-35`
- Pattern: ABC with `chat()`, `chat_from_messages()`, `stream_chat()` abstract methods; `count_tokens()` default implementation using `tiktoken`

**ConversationContext:**
- Purpose: Message list with automatic token-aware summarization
- Files: `context/context.py:11-136`
- Pattern: Encapsulated message list (`_messages: list[Message]`), token total tracking, and threshold-based summarization that replaces older messages with a summary

**ToolRegistry:**
- Purpose: Central registry mapping tool names to providers, supports namespace prefixing for disambiguation
- Files: `tool/registry.py:12-167`
- Pattern: Dict of providers -> tool lists; flat `tool_map` for O(1) lookup; optional namespaces to avoid collisions between MCP servers

## Entry Points

**CLI Entry (`python main.py`):**
- Location: `main.py`
- Triggers: Direct CLI invocation
- Responsibilities: Load config, connect to LLM, discover tools, resume or create session, run interactive REPL

**Module API (imports):**
- Location: `agent/__init__.py`, `context/__init__.py`, `session/__init__.py`, `tool/__init__.py`, `llm/__init__.py`
- Each subpackage exposes its public API via an `__init__.py` with explicit `__all__`

## Architectural Constraints

- **Threading:** Single-threaded asyncio event loop. No worker threads or process pools. Tool calls from MCP servers run on the event loop via `asyncio.gather()`, but their I/O is async.
- **Global state:** No module-level singletons. State is injected through constructors. `load_dotenv()` in `config.py` is called once at module import time.
- **Circular imports:** None detected. Dependency graph is acyclic: `main` → `agent` → `context`, `llm`, `tool`, `session`; `context` → `tool` (for ToolCall); `session` → `context`; `llm` → `config`.
- **LLM client per session:** A single `OpenAIClient` instance is shared across all sessions in a process. Sessions are isolated at the context/message level.
- **Tool provider lifecycle:** Providers are started (`start()` → `fetch_tools()`) at the beginning and shut down at the end. No hot-reload or runtime provider addition beyond initial setup.

## Anti-Patterns

### Direct Access to Private Members

**What happens:** `context._messages` is accessed directly from `session/models.py` (lines 60, 75) and `Session.mark_saved()` (line 75). `Session` reaches into `ConversationContext._messages` and `ConversationContext._last_saved_count` directly.
**Why it's wrong:** Breaks encapsulation. If `ConversationContext` internal structure changes, `Session` breaks too.
**Do this instead:** Add explicit public methods on `ConversationContext` for message iteration count and iteration, e.g., `message_count` property and a method to serialize messages. See `context/context.py` pattern.

### Stub Implementation

**What happens:** `OpenAIClient.stream_chat()` raises `NotImplementedError` (`llm/openai_client.py:97-98`). `stream_chat` is declared in `BaseLLMClient` as abstract.
**Why it's wrong:** The abstract method suggests streaming is a supported feature, but it's not implemented. Callers have no way to know this at compile time.
**Do this instead:** Either implement streaming, or remove the abstract method and provide a concrete default that raises `NotImplementedError` with a clear message.

### Unused Abstract Method

**What happens:** `BaseLLMClient.chat()` is abstract (`llm/base.py:14-16`) but is never called anywhere in the codebase. Only `chat_from_messages()` is used by `Agent.run()`.
**Why it's wrong**: Dead code surface that must be implemented by any future LLM client but is never invoked.
**Do this instead**: Remove the unused abstract method or implement a caller.

## Error Handling

**Strategy:** Wrap errors at layer boundaries; log at point of failure.

**Patterns:**
- **LLM errors**: `APIConnectionError` / `APIError` from OpenAI SDK caught and re-raised as domain exceptions `LLMConnectionError` / `LLMResponseError` (`llm/openai_client.py:66-72`)
- **Tool errors**: Exceptions from tool calls caught in `asyncio.gather(return_exceptions=True)` and returned as error strings to the LLM (`agent/core.py:93-101`)
- **Provider failures**: `start()` and `shutdown()` failures logged but do not crash the process (`tool/registry.py:54-55`, `60-62`)
- **Session corruption**: Corrupt JSONL files are logged and skipped in `list_sessions()` and `load()` (`session/store.py:74-76`, `103-104`)
- **Summarization failure**: Exceptions during summarization are caught and logged; operation is silently skipped (`context/context.py:111-113`)

## Cross-Cutting Concerns

**Logging:** Python `logging` module throughout. Level: INFO in `main.py:14` via `basicConfig`. Format: `"%(levelname)s: %(message)s"`.
- Key log points: LLM calls, tool calls (with timing), provider registration, summarization events.
- No structured logging or correlation IDs across layers.

**Validation:** Minimal. `Message.__post_init__` validates role against `VALID_ROLES` (`context/message.py:18-20`). Tool input schema validation is left to individual providers (built-in tools do not validate schemas).

**Authentication:** None for the app itself. API key for the LLM backend is loaded from `OPENAI_API_KEY` env var and passed to `AsyncOpenAI` (`config.py:13`, `llm/openai_client.py:19`).

---

*Architecture analysis: 2026-07-25*
