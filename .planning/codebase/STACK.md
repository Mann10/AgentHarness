# Technology Stack

**Analysis Date:** 2026-07-25

## Languages

**Primary:**
- Python 3.12.5 - All application source code (`*.py` under `agent/`, `llm/`, `tool/`, `session/`, `context/`, plus `main.py` and `config.py`)

**Secondary:**
- JavaScript/Node.js — OpenCode plugin system (`.opencode/plugins/graphify.js`). Not part of the core agent harness runtime.

## Runtime

**Environment:**
- Python 3.12.5 (CPython, installed at `C:\Users\kanga\AppData\Local\Programs\Python\Python312`)
- Project runs in a virtual environment at `venv/` (created from the system Python)

**Package Manager:**
- pip 24.2
- Lockfile: Not detected (no `requirements.txt.lock` or `Pipfile.lock` present)
- Dependency specification: `requirements.txt` (5 packages)

## Frameworks

**Core (Agent Harness):**
- No web framework — this is a **terminal-based interactive agent** (`main.py`, line 195-218: `input()` REPL loop via `asyncio.to_thread`)
- **asyncio** (stdlib) — async event loop for LLM calls and tool orchestration (`main.py:228`, `agent/core.py:93`)

**Testing:**
- Not detected — no test files, test runner config, or test directories found

**MCP (Model Context Protocol):**
- `mcp>=1.27,<2` — Client SDK for the Model Context Protocol (`tool/mcp_provider.py`). Used to connect to external MCP-compatible tool servers via stdio or HTTP.

**Build/Dev:**
- Not detected — no build system, no task runner, no CI config

## Key Dependencies (`requirements.txt`)

**Critical:**
- `openai>=1.0.0` — Official OpenAI Python SDK (`llm/openai_client.py`). Used for all LLM API calls via `AsyncOpenAI` (line 18). Compatible with any OpenAI-compatible API endpoint.
- `mcp>=1.27,<2` — MCP client library (`tool/mcp_provider.py`). Manages connections to MCP tool servers via stdio or HTTP SSE.

**Infrastructure:**
- `python-dotenv>=1.0.0` — Loads `.env` file into environment variables (`config.py:6`, `load_dotenv()`)
- `tiktoken>=0.7.0` — OpenAI's tokenizer, used for token counting (`llm/base.py:30-33`, fallback to whitespace split on error)
- `graphifyy>=0.9` — Knowledge graph library (invoked via `graphify` CLI, required by the project's `AGENTS.md` workflow)

**Application Layer (OpenCode):**
- `@opencode-ai/plugin@1.18.4` — Node package installed under `.opencode/` for OpenCode IDE plugin support

## Configuration

**Environment (`.env` — NOT committed, `.env.example` shows shape):**
- `OPENAI_BASE_URL` — Base URL for OpenAI-compatible API (default: `http://localhost:20128/v1`)
- `OPENAI_MODEL` — Model identifier (default: `free-stack`)
- `OPENAI_API_KEY` — API key for authentication

**Application:**
- `config.py` — `Config` dataclass loaded from environment variables (lines 9-17):
  - `temperature` (default: 0.7)
  - `max_tokens` (default: 4096)
  - `system_prompt` (default: "You are a helpful assistant.")
  - `mcp_config_path` (default: `mcp_servers.json`)

**MCP Servers:**
- `mcp_servers.json` — JSON file listing MCP server configurations (currently empty: `{"mcpServers": []}`)

**OpenCode:**
- `.opencode/opencode.json` — Plugin config loading `graphify.js` plugin
- `AGENTS.md` — GSD (Get Shit Done) workflow rules with graphify integration

## Platform Requirements

**Development:**
- Python 3.12+
- pip (for installing `requirements.txt`)
- OpenAI-compatible API endpoint (default: localhost:20128)

**Production:**
- Not specified — no deployment configuration, no Dockerfile, no hosting setup

---

*Stack analysis: 2026-07-25*
