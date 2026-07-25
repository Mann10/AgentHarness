# External Integrations

**Analysis Date:** 2026-07-25

## APIs & External Services

**LLM Provider (OpenAI-Compatible):**
- **Service:** Any OpenAI-compatible chat completion API (default: `http://localhost:20128/v1`)
  - SDK/Client: `openai>=1.0.0` (`llm/openai_client.py`)
  - Auth: `OPENAI_API_KEY` env var (`config.py:13`)
  - Endpoint: `POST /chat/completions` via `AsyncOpenAI().chat.completions.create()` (line 58)
  - Configurable: Base URL (`OPENAI_BASE_URL`), model (`OPENAI_MODEL`), temperature, max_tokens
  - Error handling: `APIConnectionError` → `LLMConnectionError`, `APIError` → `LLMResponseError` (`llm/errors.py`)

## Data Storage

**Session Persistence:**
- **Type:** Local JSONL files
  - Location: `.agentharness/<session_id>.jsonl` (`session/store.py:40`)
  - Format: First line is a meta JSON object, subsequent lines are message event JSON objects
  - Client: `JSONLSessionStore` (`session/store.py:31-105`)
  - Schema: `SessionSummary` (id, title, timestamps, message_count) and `Session` with full event history

**Knowledge Graph (Graphify):**
- **Type:** Local JSON + HTML files
  - Location: `graphify-out/graph.json`, `graphify-out/GRAPH_REPORT.md`, `graphify-out/graph.html`
  - Client: `graphify` CLI (Python package `graphifyy>=0.9`)
  - Cache: `graphify-out/cache/` (for incremental re-extraction)

**File Storage:**
- Local filesystem only. Built-in tools (`tool/local_provider.py`) support read/write via `read_file`, `write_file`, `list_dir`.

**Caching:**
- **Service:** None (no Redis, Memcached, or similar)

## Authentication & Identity

**Auth Provider:**
- **Service:** None built-in. The `config.py:13` accepts an `OPENAI_API_KEY` passed directly to the OpenAI SDK.
- No user authentication, no OAuth, no identity management.

## Monitoring & Observability

**Error Tracking:**
- **Service:** None (no Sentry, Datadog, or similar)

**Logs:**
- **Approach:** Python `logging` module with INFO level (`main.py:14`: `logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")`)
- Logged events: Tool calls, tool results, session operations, MCP provider lifecycle
- No structured logging, no log aggregation, no log rotation

## CI/CD & Deployment

**Hosting:**
- **Platform:** None — terminal-only application, no web server, no deployment target

**CI Pipeline:**
- **Service:** None detected (no `.github/workflows/`, no `.gitlab-ci.yml`, no `Jenkinsfile`)

## Environment Configuration

**Required env vars (in `.env.example`):**
- `OPENAI_BASE_URL` — LLM API endpoint (default: `http://localhost:20128/v1`)
- `OPENAI_MODEL` — Model name (default: `free-stack`)
- `OPENAI_API_KEY` — API key (currently optional, defaults to `""`)

**Optional env vars (from `config.py`):**
- `SYSTEM_PROMPT` — System prompt override
- `TEMPERATURE` — LLM temperature (default: 0.7)
- `MAX_TOKENS` — Max tokens per response (default: 4096)
- `MCP_CONFIG_PATH` — Path to MCP server config (default: `mcp_servers.json`)

**Secrets location:**
- `.env` file in project root (gitignored)
- `.env.example` shows the template

## MCP Server Integration

**Protocol:**
- **Standard:** Model Context Protocol (`mcp>=1.27,<2`)
- **Transports:** Stdio (`tool/mcp_provider.py:33-46`) and HTTP SSE via `streamable_http_client()` (line 48-68)

**Configuration:**
- `mcp_servers.json` — Defines MCP servers with name, command/url, args, env, headers, namespace
- Loaded by `ToolRegistry.load_config()` (`tool/registry.py:19-32`)

**Current state:** Empty (`mcp_servers.json`: `{"mcpServers": []}`) — no MCP servers configured by default

**Tool namespace support:**
- MCP tools can be namespaced to avoid collisions (`tool/registry.py:127-131`, `tool/config.py:12`)
- Namespace prefix: `<namespace>_<tool_name>` (e.g., `github_search_repos`)

## Webhooks & Callbacks

**Incoming:**
- None — no HTTP server, no webhook endpoints

**Outgoing:**
- None — no outbound webhooks or callback URLs

## Extensibility Points

**Local Built-in Tools** (`tool/local_provider.py`):
- `read_file` — Read file from local filesystem
- `write_file` — Write content to local filesystem (creates parent directories)
- `list_dir` — List directory contents
- Registration via `register_builtin_tools()` (line 87-138)

**GSD Workflow System** (`.opencode/commands/gsd/`, `.opencode/skills/`):
- 13 GSD workflow skills for planning, execution, review, and verification
- 33 subagents defined in `.opencode/agents/` for various roles
- Not external integrations per se, but a built-in workflow orchestration layer

---

*Integration audit: 2026-07-25*
