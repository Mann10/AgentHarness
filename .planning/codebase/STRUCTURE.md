# Codebase Structure

**Analysis Date:** 2026-07-25

## Directory Layout

```
AgentHarness/
├── main.py                    # CLI entry point — interactive REPL
├── config.py                  # Environment-based configuration
├── requirements.txt           # Python dependencies
├── mcp_servers.json           # MCP server definitions
├── AGENTS.md                  # Project-level agent instructions
├── .env.example               # Environment variable template
├── .gitignore
│
├── agent/                     # Agent orchestration layer
│   ├── __init__.py
│   ├── core.py                # Agent class — LLM↔tool run loop
│   └── result.py              # AgentResult dataclass
│
├── context/                   # Conversation context management
│   ├── __init__.py
│   ├── context.py             # ConversationContext — messages + summarization
│   └── message.py             # Message dataclass
│
├── session/                   # Session persistence
│   ├── __init__.py
│   ├── models.py              # Session, SessionSummary — state + serialization
│   └── store.py               # SessionStore ABC, JSONLSessionStore
│
├── llm/                       # LLM client abstraction
│   ├── __init__.py
│   ├── base.py                # BaseLLMClient ABC
│   ├── openai_client.py       # OpenAIClient — OpenAI SDK adapter
│   └── errors.py              # LLMError hierarchy
│
├── tool/                      # Tool system
│   ├── __init__.py
│   ├── models.py              # Tool, ToolCall, ToolResult, LLMResponse, ToolProvider protocol
│   ├── registry.py            # ToolRegistry — provider + name resolution
│   ├── config.py              # MCPConfig, MCPServerConfig dataclasses
│   ├── local_provider.py      # LocalToolProvider + built-in tools (read_file, write_file, list_dir)
│   └── mcp_provider.py        # MCPToolProvider — stdio + HTTP transport
│
├── .opencode/                 # OpenCode AI configuration
│   ├── opencode.json          # Plugin registration
│   ├── commands/              # Custom commands
│   ├── skills/                # Agent skills
│   ├── agents/                # Agent definitions
│   ├── rules/                 # Code rules
│   └── plugins/               # Plugins (e.g., graphify.js)
│
├── .planning/                 # GSD planning artifacts
│   └── codebase/              # Codebase analysis docs (this file)
│
├── graphify-out/              # Knowledge graph output
│   ├── graph.json             # Main knowledge graph
│   ├── GRAPH_REPORT.md        # Graph analysis report
│   ├── graph.html             # Interactive graph visualization
│   └── cache/                 # Cache (gitignored)
│
├── .agentharness/             # Session persistence files (gitignored)
│   └── *.jsonl                # One JSONL file per session
│
├── plans/                     # Development plans (markdown)
│   ├── tool-mcp-module.md
│   ├── session-module.md
│   ├── llm-client-refactor.md
│   └── context-layer.md
│
└── venv/                      # Python virtual environment (gitignored)
```

## Directory Purposes

**`agent/`:**
- Purpose: Agent orchestration — manages the conversation loop between LLM and tools
- Contains: `core.py` (main Agent class), `result.py` (AgentResult dataclass), `__init__.py`
- Key files: `agent/core.py` (130 lines — primary orchestration logic)

**`context/`:**
- Purpose: Conversation message management with automatic token-aware summarization
- Contains: `context.py` (ConversationContext), `message.py` (Message dataclass), `__init__.py`
- Key files: `context/context.py` (136 lines), `context/message.py` (33 lines)

**`session/`:**
- Purpose: Session state management and persistence to JSONL files
- Contains: `models.py` (Session + SessionSummary), `store.py` (SessionStore ABC + JSONLSessionStore), `__init__.py`
- Key files: `session/models.py` (146 lines), `session/store.py` (105 lines)

**`llm/`:**
- Purpose: LLM client abstraction — currently OpenAI-compatible only
- Contains: `base.py` (BaseLLMClient ABC), `openai_client.py` (OpenAIClient), `errors.py` (LLMError/LLMConnectionError/LLMResponseError), `__init__.py`
- Key files: `llm/openai_client.py` (98 lines)

**`tool/`:**
- Purpose: Tool system — provider registration, MCP integration, built-in tools
- Contains: `registry.py` (ToolRegistry), `models.py` (Tool/ToolCall/ToolResult/ToolProvider), `config.py` (MCPConfig), `local_provider.py` (LocalToolProvider + built-ins), `mcp_provider.py` (MCPToolProvider), `__init__.py`
- Key files: `tool/registry.py` (178 lines), `tool/local_provider.py` (138 lines), `tool/mcp_provider.py` (116 lines)

**`.opencode/`:**
- Purpose: OpenCode AI IDE configuration — agent skills, commands, rules, plugins
- Contains: `opencode.json`, `commands/`, `skills/`, `agents/`, `rules/`, `plugins/`, `sdk/`
- Generated: No
- Committed: Yes

**`graphify-out/`:**
- Purpose: Knowledge graph output from the graphify tool — used for codebase navigation
- Contains: `graph.json`, `GRAPH_REPORT.md`, `graph.html`, historical snapshots
- Generated: Yes (by `graphify` tool)
- Committed: Yes (except `cache/`)

**`.agentharness/`:**
- Purpose: Runtime session persistence — one JSONL file per conversation session
- Contains: `*.jsonl` files
- Generated: Yes
- Committed: No (in `.gitignore`)

## Key File Locations

**Entry Points:**
- `main.py`: CLI entry point — configures all subsystems, runs interactive REPL

**Configuration:**
- `config.py`: Environment variable config via dataclass + `python-dotenv`
- `mcp_servers.json`: MCP server definitions (command/url, args, env, namespace)
- `.env.example`: Template for required environment variables

**Core Logic:**
- `agent/core.py`: Agent conversation loop (orchestrates LLM calls and tool execution)
- `context/context.py`: Message history with automatic summarization
- `session/models.py`: Session serialization/deserialization
- `session/store.py`: JSONL-based session persistence
- `llm/openai_client.py`: OpenAI API adapter
- `tool/registry.py`: Tool provider registration and name resolution
- `tool/mcp_provider.py`: MCP protocol client (stdio + HTTP SSE)
- `tool/local_provider.py`: Built-in tools (read/write files, list directory)

**Testing:**
- No test directory or test files detected in the repository

**Project Configuration:**
- `requirements.txt`: Python dependencies (openai, python-dotenv, tiktoken, mcp, graphifyy)
- `.opencode/opencode.json`: OpenCode plugin registration
- `.gitignore`: Standard ignores (.env, __pycache__, venv, .agentharness, graphify-out/cache/)

## Naming Conventions

**Files:**
- Python modules: `snake_case.py` (e.g., `openai_client.py`, `local_provider.py`, `mcp_provider.py`)
- Special files: `__init__.py` for package exports
- Config files: `kebab-case.config.*` or `snake_case.*` (e.g., `mcp_servers.json`, `opencode.json`)

**Directories:**
- All lowercase, single-word names (`agent/`, `context/`, `session/`, `llm/`, `tool/`)
- Dot-prefixed for tool/IDE config (`.opencode/`, `.planning/`, `.agentharness/`)
- Kebab-case for generated artifacts (`graphify-out/`)

**Functions:**
- `snake_case()` with descriptive names (e.g., `_make_summarize_fn`, `_resolve_session`, `_handle_session_cmd`, `register_builtin_tools`)
- Leading underscore for private/helper functions

**Classes:**
- `PascalCase` for public classes (e.g., `Agent`, `AgentResult`, `ConversationContext`, `Message`, `Session`, `OpenAIClient`, `ToolRegistry`, `MCPToolProvider`, `LocalToolProvider`)
- `PascalCase` for error classes (e.g., `LLMError`, `LLMConnectionError`, `LLMResponseError`)
- `PascalCase` for dataclasses (e.g., `SessionSummary`, `ToolCall`, `ToolResult`, `MCPServerConfig`)

**Variables:**
- `snake_case` for local variables and instance attributes (e.g., `current`, `sorted_sessions`, `total_tool_calls`)
- Leading underscore for "private" instance attributes (e.g., `self._llm`, `self._registry`, `self._context`, `self._messages`)

**Types:**
- `PascalCase` for dataclasses and protocols (e.g., `ToolProvider` is a `Protocol`)

## Where to Add New Code

**New Feature (new module/package):**
- Create a new top-level directory under `AgentHarness/` with `__init__.py`
- Wire it up in `main.py` constructor chain
- Example: adding a new storage backend → create `storage/` module, implement `SessionStore` ABC

**New Tool Provider:**
- Implementation: `tool/{name}_provider.py` — implement the `ToolProvider` protocol (`start`, `shutdown`, `fetch_tools`, `call_tool`)
- Registration: Register via `ToolRegistry.add_provider()` in `main.py` (around line 167)
- Model/type: `tool/models.py` already has the protocol defined

**New LLM Backend:**
- Implementation: `llm/{name}_client.py` — subclass `BaseLLMClient` from `llm/base.py`
- Package export: Add to `llm/__init__.py`
- Wiring: Instantiate in `main.py` where `OpenAIClient` is created (line 161)

**New Built-in Tool (local):**
- Handler function: Add to `tool/local_provider.py` as a module-level function
- Registration: Call `provider.add_tool()` inside `register_builtin_tools()` (line 87)
- Follow the existing pattern: provide `name`, `description`, `input_schema` dict, and handler callable

**New Session Command (/command):**
- Add handler logic in `_handle_session_cmd()` in `main.py` (line 83)
- Follow the existing pattern: return `True` if handled, `False` to pass through to `agent.run()`

**New Configuration Value:**
- Add field to `Config` dataclass in `config.py` with env var default factory
- Add to `.env.example` if user-facing
- Wire in `main.py` or relevant module constructor

**Utilities / Shared Helpers:**
- Consider creating a `util/` or `lib/` package if shared logic emerges across modules
- Currently, helper functions are local to each module (e.g., `_arg_summary` in `agent/core.py` and `tool/registry.py` are duplicated)

## Special Directories

**`.agentharness/`:**
- Purpose: Runtime session persistence — one JSONL file per session ID
- Generated: Yes (automatically by `JSONLSessionStore`)
- Committed: No (in `.gitignore`)

**`graphify-out/`:**
- Purpose: Knowledge graph data — used by the graphify tool for codebase navigation
- Generated: Yes (by `graphify update .` or `graphify` command)
- Committed: Yes (except `cache/` subdirectory)

**`__pycache__/`:**
- Purpose: Python bytecode cache
- Generated: Yes (by Python interpreter)
- Committed: No (in `.gitignore`)

**`venv/`:**
- Purpose: Python virtual environment
- Generated: Yes (by `python -m venv`)
- Committed: No (in `.gitignore`)

---

*Structure analysis: 2026-07-25*
