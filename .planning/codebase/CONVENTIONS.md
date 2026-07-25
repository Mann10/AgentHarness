# Coding Conventions

**Analysis Date:** 2026-07-25

## Naming Patterns

**Files:**
- `snake_case.py` for all modules — e.g., `config.py`, `openai_client.py`, `local_provider.py`, `mcp_provider.py`
- `__init__.py` per package for public API re-exports

**Classes:**
- PascalCase — `Config`, `Agent`, `OpenAIClient`, `Session`, `ToolRegistry`, `ConversationContext`, `LLMResponse`
- Abstract base classes prefixed with `Base` — `BaseLLMClient` (`llm/base.py`)
- Exception classes suffixed with `Error` — `LLMError`, `LLMConnectionError`, `LLMResponseError` (`llm/errors.py`)

**Functions/Methods:**
- snake_case for all functions and methods — `add_user_message`, `load_config`, `chat_from_messages`, `register_builtin_tools`
- Private methods prefixed with single underscore `_leading_underscore` — `_call_sdk`, `_register_tools`, `_maybe_summarize`
- Module-level private functions also use `_leading_underscore` — `_read_file`, `_write_file`, `_arg_summary`, `_summarize_args`

**Variables:**
- snake_case — `user_input`, `tool_registry`, `api_tools`, `summarize_fn`
- Private instance variables prefixed with `_` — `self._llm`, `self._context`, `self._session`, `self._messages`
- No hungarian notation

**Types:**
- Type parameters use PascalCase single letters: `T` (conventional)
- Type aliases follow function naming (snake_case usage in Callable signatures)

## Code Style

**Formatting:**
- No formatter config detected (no `.editorconfig`, no `pyproject.toml`)
- Code is consistently formatted with 4-space indentation
- No trailing whitespace observed
- Line length is pragmatic (up to ~100 chars in some places, but generally <= 88)

**Linting:**
- No linter config detected (no `.pylintrc`, `ruff.toml`, `setup.cfg`, `tox.ini`)
- Linting appears to be either not enforced or enforced implicitly by the editor

**Type Style:**

```python
# PEP 604 union types (Python 3.10+) — preferred throughout
def load(self, session_id: str) -> Session | None: ...
content: str | None = None
tool_calls: list[ToolCall] | None = None

# Future annotations imported in ~52% of modules
from __future__ import annotations

# collections.abc for generic types
from collections.abc import Callable, Awaitable, Generator
```

## Import Organization

**Order:**
1. `from __future__ import annotations` (first line, when present)
2. Standard library imports — `import asyncio`, `import logging`, `from abc import ABC`, `from dataclasses import dataclass`
3. Third-party imports — `from openai import AsyncOpenAI`, `from dotenv import load_dotenv`, `from mcp import ClientSession`
4. Internal imports — `from config import Config`, `from agent import Agent`, `from llm.base import BaseLLMClient`

**Groups separated by blank lines:**
```python
from __future__ import annotations

import json
import logging

from openai import APIConnectionError, APIError, AsyncOpenAI

from config import Config
from llm.base import BaseLLMClient
from llm.errors import LLMConnectionError, LLMResponseError
```

**Internal imports use full dotted path from project root:**
```python
from context.context import ConversationContext
from session.models import Session
from tool.registry import ToolRegistry
```

**Path Aliases:**
- No path aliases or src-relative imports used
- All internal imports are absolute from project root (e.g., `from llm.base import BaseLLMClient`, not `from .base import BaseLLMClient`)

## Error Handling

**Patterns:**
- Custom exception hierarchy rooted at `LLMError` (`llm/errors.py`):
  ```python
  class LLMError(Exception): pass
  class LLMConnectionError(LLMError): pass
  class LLMResponseError(LLMError): pass
  ```
- Specific exception types caught, never bare `except:` — `APIConnectionError`, `APIError`, `JSONDecodeError`, `FileNotFoundError`, `KeyError`, `ValueError`, `IndexError`
- Tool call errors wrapped into result strings rather than raised:
  ```python
  content = (
      f"Error: {result}"
      if isinstance(result, Exception)
      else result.content
  )
  ```
  in `agent/core.py` and `tool/local_provider.py`
- Corrupt data handled gracefully with logging + `None` return:
  ```python
  except (json.JSONDecodeError, KeyError) as e:
      logger.warning("Corrupt session file %s: %s", session_id, e)
      return None
  ```
- Provider startup failures logged but not fatal — other providers continue:
  ```python
  except Exception as e:
      logger.error("Failed to start provider '%s': %s", name, e)
  ```
- `raise NotImplementedError("stream_chat not yet implemented")` in `llm/openai_client.py:98` for stubbed abstract methods

**What NOT to do:**
- Do not catch `Exception` broadly — use specific exception types
- Do not raise bare `Exception` — use or extend the existing `LLMError` hierarchy or `ValueError`

## Logging

**Framework:** Standard library `logging`

**Configuration:** Set once in `main.py:14`:
```python
logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")
```

**Patterns:**
- Module-level logger created at module scope:
  ```python
  logger = logging.getLogger(__name__)
  ```
- Log levels used appropriately:
  - `logger.info()` — lifecycle events, tool calls, high-level progress
  - `logger.warning()` — configuration missing, corrupt data, tool errors
  - `logger.error()` — provider failures, startup errors
  - `logger.debug()` — detailed arguments (only in `tool/local_provider.py` and `tool/mcp_provider.py`)
- For user-facing output (non-log), `print()` is used directly in `main.py` and `context/context.py`
- No structured logging (no JSON logs, no extra= dicts used)

## Comments

**When to Comment:**
- Sparse commenting — code is mostly self-documenting
- Section headers for logical groupings:
  ```python
  # ── Assembly ──────────────────────────────────────────
  # ── Serialization ─────────────────────────────────────
  ```
  Used in `session/models.py`
- Inline comments for non-obvious logic (rare)

**JSDoc/TSDoc:**
- No docstrings on most functions — the exception is `BaseLLMClient` abstract methods (no docstrings either)
- Tool definitions in `local_provider.py` include `description` strings embedded in the input_schema (not Python docstrings)
- No `__init__` docstrings anywhere

**Recommendation:** Add module-level docstrings and key-class docstrings to aid maintainability.

## Function Design

**Size:**
- Functions range from 1 line (`agent/result.py:4`, `tool/config.py:16`) to ~50 lines
- Largest: `main()` at ~70 lines (`main.py:158-224`)
- Private helper extraction is used to keep methods focused (`_arg_summary`, `_summarize_args`, `_resolve_session`)

**Parameters:**
- Named parameters with type annotations throughout
- Keyword-only arguments marked with `*` separator:
  ```python
  def __init__(
      self,
      llm_client: BaseLLMClient,
      tool_registry: ToolRegistry,
      session: Session,
      *,
      max_tool_iterations: int = 15,
  )
  ```
- Default parameter values provided when sensible:
  ```python
  token_limit: int, summarize_fn=None, summarize_threshold: float = 0.75
  ```

**Return Values:**
- Explicit `-> None` for void functions (consistent convention)
- `| None` union return types for optional returns: `Session | None`, `str | None`
- Dataclass instances for structured data: `AgentResult`, `LLMResponse`, `ToolResult`
- Strings for error content (wrapped as `ToolResult` rather than raising)

## Module Design

**Exports:**
- Explicit `__all__` in every `__init__.py` — controls public API surface
- Packages re-export all public types:
  ```python
  # tool/__init__.py
  from tool.config import MCPConfig, MCPServerConfig
  from tool.local_provider import LocalToolProvider, register_builtin_tools
  from tool.mcp_provider import MCPToolProvider
  from tool.models import LLMResponse, Tool, ToolCall, ToolProvider, ToolResult
  from tool.registry import ToolRegistry

  __all__ = [
      "Tool", "ToolCall", "ToolResult", "ToolProvider", "LLMResponse",
      "MCPServerConfig", "MCPConfig", "MCPToolProvider", "LocalToolProvider",
      "ToolRegistry", "register_builtin_tools",
  ]
  ```

**Barrel Files:**
- Used consistently — every package has `__init__.py` that re-exports its public API
- Consumers import from the package, not the module:
  ```python
  from tool import ToolRegistry, LocalToolProvider  # correct
  # NOT: from tool.registry import ToolRegistry
  ```

**Package Structure:**
- Each domain module has its own `errors.py` if errors exist (only `llm/errors.py`)
- Each domain module has `models.py`, `base.py` where complexity warrants
- Config is separated into `config.py` (single file) and `tool/config.py`
- No circular imports detected

## Asynchronous Patterns

**Convention:**
- All I/O-bound methods are `async def`
- `asyncio.gather` with `return_exceptions=True` for concurrent tool execution:
  ```python
  tasks = [
      self._registry.call_tool(tc.name, tc.arguments)
      for tc in response.tool_calls
  ]
  results = await asyncio.gather(*tasks, return_exceptions=True)
  ```
- Blocking calls wrapped in `asyncio.to_thread`:
  ```python
  line = (await asyncio.to_thread(input, "> ")).strip()
  ```
- Async context managers using `__aenter__` / `__aexit__` directly (MCP provider)
- Async abstract methods declared with `@abstractmethod` on `async def`

---

*Convention analysis: 2026-07-25*
