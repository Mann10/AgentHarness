# Codebase Concerns

**Analysis Date:** 2026-07-25

## Tech Debt

### Bug: Undefined Variable `system_msgs` in Summarization

**Issue:** `context/context.py` line 125 references `system_msgs` which is never defined. This will cause a `NameError` at runtime when `_maybe_summarize()` is triggered.

**Files:**
- `context/context.py:125` — `self._messages.insert(len(system_msgs), summary_msg)`

**Impact:** When conversation token usage exceeds the threshold (`total_tokens > token_limit * 0.75`), summarization fires and hits a crash. The context manager becomes inoperable. This makes the summarization feature non-functional in production.

**Fix approach:** Replace `system_msgs` with `0` (the context no longer owns system messages — they were moved to `session/models.py`). The insert index should be `0` to place the summary at the start of conversation messages.

### Inefficient O(n²) Message Removal During Summarization

**Issue:** In `context/context.py` lines 121-123, summarization removes messages one by one using `self._messages.remove(m)` inside a loop. Each `remove()` scans the list from the beginning, making this O(n²) in the number of messages to remove.

**Files:**
- `context/context.py:121-123`

**Impact:** On long-running sessions with many messages, summarization can become progressively slower. For sessions with 1000+ messages, this could cause noticeable pauses.

**Fix approach:** Replace the loop with a list comprehension that filters out the summarized messages in O(n):
```python
to_summarize_set = set(to_summarize)
self._messages = [m for m in self._messages if m not in to_summarize_set]
```

### `query`/`alias` on Provider Not Used in `ToolRegistry`

**Issue:** The `ToolProvider` protocol in `tool/models.py` defines `async def start()`, `shutdown()`, `fetch_tools()`, and `call_tool()`. Both `MCPToolProvider` and `LocalToolProvider` implement these, but only `call_tool()` and `fetch_tools()` are exercised. The `start()/shutdown()` lifecycle is called in `registry.py` but there's no health-check or reconnection path if an MCP server disconnects mid-session.

**Files:**
- `tool/registry.py`
- `tool/mcp_provider.py`

**Impact:** If an MCP server process crashes or the HTTP connection drops during a session, there is no recovery path. The provider remains registered but non-functional, causing tool calls to fail with opaque errors.

**Fix approach:** Add a health-check wrapper in `ToolRegistry.call_tool()` that catches transport errors, marks the provider's tools as unavailable, and returns a clear error message to the LLM.

### Missing `remove_provider()` Implementation

**Issue:** The `session-module.md` plan (plans/session-module.md) specifies `remove_provider()` on `ToolRegistry`, but it was never implemented in `tool/registry.py`.

**Files:**
- `tool/registry.py` (missing method)
- `plans/session-module.md` (specifies it)

**Impact:** No way to dynamically unregister a provider that has failed or is no longer needed. The provider list only grows, and failed providers accumulate.

### Inconsistent Session Store Directory

**Issue:** The `session-module.md` plan specifies the session store directory as `~/.agentharness/projects/{sha256(cwd)[:16]}/` using a hash of the CWD. The actual implementation in `session/store.py` uses `Path.cwd() / ".agentharness"` instead — a project-local directory.

**Files:**
- `session/store.py:34-36` (actual implementation)
- `plans/session-module.md` (planned implementation)

**Impact:** Sessions are stored in the project directory, meaning they get committed to git if `.agentharness/` isn't in `.gitignore` (it currently is). However, this path is not portable — if the project is cloned elsewhere, past sessions don't follow the user. The planned global directory was a better design.

### `__pycache__` at Project Root

**Issue:** Compiled bytecode files (`config.cpython-312.pyc`, `llm.cpython-312.pyc`, `main.cpython-312.pyc`) exist at the project root in `__pycache__/`. This is a side effect of running `python main.py` from the project root without proper package structure. These files should be excluded from version control (currently they are not in `.gitignore`).

**Files:**
- `__pycache__/` (directory at project root)
- `.gitignore` (does not exclude root `__pycache__/`)

**Impact:** Unnecessary files may be committed. The top-level `__pycache__` is a sign that the project should be restructured as a proper Python package.

## Known Bugs

### Summarization Crashes with `NameError` (Critical)

**Issue:** As detailed above under Tech Debt, `context/context.py:125` references undefined variable `system_msgs`.

**Symptoms:** When `ConversationContext._maybe_summarize()` is called (triggered when `total_tokens > token_limit * 0.75`), the following crash occurs:
```
NameError: name 'system_msgs' is not defined
```

**Files:**
- `context/context.py:125`

**Trigger:** Long conversations where token count exceeds 75% of `max_tokens` (default 3072 tokens for a 4096 limit).

**Workaround:** Set `MAX_TOKENS` environment variable high enough that summarization is never triggered, or set `summarize_fn` to `None` to disable summarization entirely.

### `stream_chat()` Always Raises `NotImplementedError`

**Issue:** The `stream_chat()` abstract method in `llm/base.py` is required by the `BaseLLMClient` ABC, but `OpenAIClient` raises `NotImplementedError` for it.

**Files:**
- `llm/base.py:24-26` (abstract method definition)
- `llm/openai_client.py:96-98` (raises NotImplementedError)

**Impact:** Any code path attempting to use streaming will crash. The method signature in the ABC forces subclasses to implement it, but only one client exists and it doesn't support streaming.

**Fix approach:** Either implement streaming in `OpenAIClient` or remove the abstract method from `BaseLLMClient` if streaming is not planned.

### Inconsistent `chat_from_messages()` Type Annotation

**Issue:** The `BaseLLMClient.chat_from_messages()` signature declares `tools: list[dict] | None = None`, but the actual usage passes `list[Tool]` objects (from `ToolRegistry.list_tools()`). The `OpenAIClient._call_sdk()` handles both types at runtime via duck-typing, but the type annotation in the base class is incorrect.

**Files:**
- `llm/base.py:20-21` (incorrect annotation)
- `llm/openai_client.py:28-31` (accepts but overrides with different signature)
- `agent/core.py:57-58` (passes `list[Tool]`)

**Impact:** Type checkers will flag valid usage as errors. The corrected annotation should be `list[Tool] | list[dict] | None`.

## Security Considerations

### Built-in File Tools Have No Path Restrictions

**Issue:** The built-in tools `read_file`, `write_file`, and `list_dir` in `tool/local_provider.py` accept arbitrary filesystem paths with no sandboxing or path traversal protection. The LLM could read or write any file the process has access to.

**Files:**
- `tool/local_provider.py:54-84` (`_read_file`, `_write_file`, `_list_dir`)

**Current mitigation:** None. Paths are used as-is with `os.path.isfile()`/`os.path.isdir()` checks.

**Recommendations:**
- Add a configurable allowed directory whitelist (default to project root).
- Resolve all paths to absolute form and verify they start with the allowed base.
- Block path traversal sequences (`../`, `..\\`, symlink escapes).
- Consider read-only mode as a config option.

### No Input Validation on Tool Arguments

**Issue:** Tool argument dictionaries from the LLM are passed directly to handler functions with no schema validation beyond what the OpenAI API enforces for JSON structure. Arguments are not type-checked or sanitized.

**Files:**
- `tool/local_provider.py:54-84`
- `tool/mcp_provider.py:92-116`

**Current mitigation:** Only the MCP SDK's built-in parameter validation.

**Recommendations:** Validate tool inputs against the declared `input_schema` before dispatching to handlers.

### API Key in Process Memory

**Issue:** The OpenAI API key (from `OPENAI_API_KEY` env var) is stored in `Config.api_key` as a plain string and passed to `AsyncOpenAI(api_key=...)`. It remains in memory for the lifetime of the process.

**Files:**
- `config.py:13`
- `llm/openai_client.py:18-21`

**Recommendations:** This is acceptable for a local CLI tool, but if the harness is ever used in a shared environment or as a server, key rotation and secure credential storage should be added.

### `.env` File Present

**Issue:** A `.env` file exists at the project root. While `.env` is listed in `.gitignore`, the file may contain API keys and sensitive configuration. The `.env` in `.opencode/` is NOT in `.gitignore` (`.opencode` is in `.gitignore` but the `.env` within it could leak if `.opencode` gitignore rule is removed).

**Files:**
- `.env` (project root — gitignored)
- `.opencode/.env` (in `.opencode/` which is gitignored)

**Current mitigation:** `.env` is in `.gitignore`. `.opencode/` is in `.gitignore`.

## Performance Bottlenecks

### Full Session Load Into Memory

**Issue:** `JSONLSessionStore.load()` reads the entire JSONL file into memory, parsing every line into a list of events, then replaying all messages into `ConversationContext`. For sessions with 10,000+ messages, this could consume significant memory and cause slow startup.

**Files:**
- `session/store.py:60-76`
- `session/models.py:103-123`

**Cause:** The JSONL format is append-only with no indexing. Every load must scan from the beginning to reconstruct state.

**Improvement path:** Implement lazy-loading or pagination by timestamp. Add a message count to the meta line and an optional index sidecar.

### Sequential Session Listing Reads Every File Twice

**Issue:** `JSONLSessionStore.list_sessions()` opens each JSONL file, reads the first line for metadata, then opens it again to count message lines by scanning the entire file.

**Files:**
- `session/store.py:81-104`

**Improvement path:** Cache message count in the meta line or maintain a separate index file. For v1, at least combine both operations into a single file read per session.

### All Tool Calls Execute in a Single Gather

**Issue:** In `agent/core.py:89-93`, all tool calls from a single LLM response are dispatched concurrently via `asyncio.gather`. While this is intentional for parallelism, it provides no ordering guarantees and no throttling. If one tool call is fast and another is slow, the fast result is blocked by the slow one before the LLM sees any results.

**Files:**
- `agent/core.py:89-93`

**Improvement path:** Consider streaming intermediate results to the LLM as they complete, or at least adding a configurable concurrency limit.

## Fragile Areas

### `Session._build_system_prompt()` Reads AGENTS.md Every Turn

**Issue:** Every call to `to_llm_messages()` (which happens on every LLM request) reads `AGENTS.md` from disk via `Path("AGENTS.md").read_text()`. If the file is large, this adds disk I/O to every turn. If the file is deleted mid-session, the read will raise `FileNotFoundError`.

**Files:**
- `session/models.py:48-54`

**Why fragile:** The relative path assumes the CWD is the project root. If the harness is launched from a different directory, `AGENTS.md` won't be found. No error handling for missing/unreadable file.

**Safe modification:** Add error handling for `FileNotFoundError` and `PermissionError`. Cache the file contents with an invalidation mechanism (e.g., mtime check) rather than re-reading on every turn.

### `ConversationContext._messages` Accessed Directly via Private Attribute

**Issue:** Several external classes access `self._context._messages` directly — a private attribute. This creates tight coupling:

**Files:**
- `session/models.py:60` — `self._context._messages` in `to_events()`
- `session/models.py:75` — `self._context._messages` in `mark_saved()`
- `agent/core.py` — accesses `self._context` (which is `self._session.context`)

**Why fragile:** Any change to the `ConversationContext` internal representation (e.g., renaming `_messages` or changing from list to deque) silently breaks three other modules. Python name mangling doesn't help since these are single-underscore privates.

**Safe modification:** Add a public `message_count` property and a `get_messages()` or `__iter__` method to `ConversationContext`. Deprecate direct `_messages` access.

### `LocalToolProvider` Handler Signature Mismatch

**Issue:** The type annotation for `LocalToolProvider.add_tool()` declares `handler: Callable[[dict], str]`, but `_write_file` returns the result of `str.format()` (a `str`), `_list_dir` returns `"\n".join(lines)` (a `str`), and `_read_file` returns `f.read()` (a `str`). While correct now, the return type annotation on the handler is `str`, but `call_tool()` wraps non-exception results with `ToolResult(tool_call_id=name, content=str(result))`, which means if a handler ever returns a non-string, it gets silently stringified.

**Files:**
- `tool/local_provider.py:17-27`

**Safe modification:** Change handler type to `Callable[[dict], str]` (which is correct) and ensure error paths in `call_tool()` don't double-stringify.

### MCP Error Content Handling is Incomplete

**Issue:** In `tool/mcp_provider.py:100-108`, when an MCP tool returns `result.isError`, only `TextContent` items are extracted as error text. Other content types (image, embedded resources) are silently dropped.

**Files:**
- `tool/mcp_provider.py:100-113`

**Why fragile:** If an MCP server returns rich error content (e.g., `ImageContent`, `EmbeddedResource`), the error message will be empty, and the LLM sees a non-descriptive error.

## Scaling Limits

### Single-threaded Async REPL with Blocking Input

**Issue:** The REPL loop in `main.py` uses `asyncio.to_thread(input, "> ")` which runs the blocking `input()` call in a thread pool. This is correct, but the overall architecture is single-user with no concurrent session support.

**Files:**
- `main.py:197`

**Current capacity:** Single user, single session at a time.

**Limit:** Cannot handle concurrent users or background tasks. Session switching (`/resume`) saves and loads from disk every time.

**Scaling path:** For multi-user scenarios, the session store would need a proper database backend, and the REPL would need to become a server with WebSocket connections.

### JSONL Format Not Suitable for Production

**Issue:** The JSONL session store (`session/store.py`) is an append-only log with no indexing, compaction, or corruption recovery.

**Files:**
- `session/store.py:42-58`

**Current capacity:** Adequate for single-user CLI with dozens of sessions.

**Limit:** Files grow unboundedly. No compaction means deleted/edited messages leave ghost entries. No checksumming means silent corruption goes undetected.

## Dependencies at Risk

### `mcp` Python SDK on Version Constraint

**Issue:** `requirements.txt` pins `mcp>=1.27,<2`. The MCP protocol is still evolving, and major version bumps could break the streamable HTTP transport or the `ClientSession` API.

**Files:**
- `requirements.txt:4`
- `tool/mcp_provider.py` (uses `stdio_client`, `streamable_http_client`, `ClientSession`)

**Risk:** A breaking change in `mcp>=2.0.0` would require migration. The `streamable_http_client` import path (`mcp.client.streamable_http`) is especially likely to change as the SSE vs. Streamable HTTP debate settles.

**Migration plan:** Keep the `<2` upper bound. Monitor MCP SDK releases. When v2 lands, test against the `openai`-compatible tool call format as a fallback.

### `openai` SDK Async Client Usage

**Issue:** The `openai` SDK `AsyncOpenAI` client is used but the version is unconstrained (`openai>=1.0.0`). Major API changes in the SDK could break the `chat.completions.create()` call.

**Files:**
- `requirements.txt:1`
- `llm/openai_client.py:58-65`

**Risk:** Low — the OpenAI SDK is stable at v1.x, but unconstrained versioning means `pip install` could pull a future incompatible version.

## Testing Coverage Gaps

### No Tests Exist

**Issue:** The project has zero test files. There are no unit tests, integration tests, or end-to-end tests anywhere in the codebase.

**Files:** (entire project)

**What's not tested:**
- `ConversationContext` summarization logic (which has a known crash bug — see above)
- `ToolRegistry` namespace resolution and collision detection
- `JSONLSessionStore` append-only save/load round-trip
- `OpenAIClient` tool call parsing and error handling
- `Agent.run()` tool iteration loop and forced response path
- Built-in tools (`read_file`, `write_file`, `list_dir`)
- MCP provider connection, tool discovery, error handling
- Session serialization/deserialization

**Risk:** The known `system_msgs` bug in `context/context.py` was not caught by tests. Any refactoring risks silent regressions. The tool namespace collision logic in `registry.py` is complex and untested.

**Priority:** High

### No Linting or Type Checking Configuration

**Issue:** There is no `pyproject.toml`, `setup.cfg`, `.pylintrc`, or `mypy.ini` configuration. Type annotations exist but are not enforced. No pre-commit hooks or CI checks.

**Files:** (missing configuration files)

**Risk:** Type errors (like the `chat_from_messages` annotation) and import issues are not caught automatically.

---

*Concerns audit: 2026-07-25*
