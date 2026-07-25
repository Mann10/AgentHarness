# Testing Patterns

**Analysis Date:** 2026-07-25

## Test Framework

**Runner:**
- Not detected — no test runner is configured in the project
- No `pytest`, `unittest`, or alternative test framework found
- No test configuration files exist (`pytest.ini`, `pyproject.toml` with pytest config, `setup.cfg`, `tox.ini`, `conftest.py`, etc.)

**Assertion Library:**
- Not applicable — no test files exist

**Run Commands:**
- No test commands defined — no `Makefile`, no `tox.ini`, no script entries in any config
- Recommendation: Add pytest as a dev dependency and configure basic test commands

## Test File Organization

**Location:**
- No test directory exists — no `tests/` folder, no `test_` files co-located with source
- Recommendation: Create a `tests/` directory mirroring the source structure:
  ```
  tests/
  ├── test_agent/
  │   ├── test_core.py
  │   └── test_result.py
  ├── test_llm/
  │   ├── test_base.py
  │   ├── test_openai_client.py
  │   └── test_errors.py
  ├── test_session/
  │   ├── test_models.py
  │   └── test_store.py
  ├── test_tool/
  │   ├── test_models.py
  │   ├── test_registry.py
  │   ├── test_config.py
  │   ├── test_local_provider.py
  │   └── test_mcp_provider.py
  ├── test_context/
  │   ├── test_message.py
  │   └── test_context.py
  └── test_config.py
  ```

**Naming:**
- No test files exist, so no naming convention established
- Recommended convention: `test_<module_name>.py` with `def test_<function_name>()`

## Test Structure

No test suites exist in the codebase. Every source file has zero test coverage.

**Recommended patterns based on codebase architecture:**

```python
# tests/test_tool/test_models.py
from tool.models import Tool, ToolCall, ToolResult, LLMResponse


def test_tool_dataclass():
    tool = Tool(name="test", description="A test tool", input_schema={"type": "object"})
    assert tool.name == "test"
    assert tool.description == "A test tool"
    assert tool.input_schema == {"type": "object"}


def test_tool_call_dataclass():
    tc = ToolCall(id="call_1", name="read_file", arguments={"path": "/tmp/test.txt"})
    assert tc.id == "call_1"
    assert tc.name == "read_file"
    assert tc.arguments == {"path": "/tmp/test.txt"}
```

## Mocking

**Framework:**
- No mocking framework is installed or configured
- `unittest.mock` (stdlib) would be the natural choice given no other test dependencies
- Recommendation: Use `unittest.mock` or `pytest-mock` for mocking

**What to Mock:**
- `AsyncOpenAI` client in `llm/openai_client.py` — WARNING: do not mock during integration tests
- MCP `ClientSession` in `tool/mcp_provider.py` — external process I/O
- `JSONLSessionStore` file I/O in `session/store.py` — filesystem operations
- `Config` values for different environment configurations

**What NOT to Mock:**
- Dataclasses (`Tool`, `ToolCall`, `ToolResult`, `LLMResponse`, `Message`) — plain data objects
- `ConversationContext` — use real instance with mock `count_tokens` callable
- Error classes (`LLMError`, `LLMConnectionError`, `LLMResponseError`) — simple exception classes

## Fixtures and Factories

No fixtures exist.

**Recommended test data pattern (based on existing models):**

```python
import pytest
from tool.models import Tool, ToolCall, ToolResult, LLMResponse
from context.message import Message


@pytest.fixture
def sample_tool():
    return Tool(
        name="read_file",
        description="Read the contents of a file",
        input_schema={
            "type": "object",
            "properties": {"path": {"type": "string"}},
            "required": ["path"],
        },
    )


@pytest.fixture
def sample_tool_call():
    return ToolCall(id="tc_1", name="read_file", arguments={"path": "/tmp/test.txt"})


@pytest.fixture
def sample_tool_result():
    return ToolResult(tool_call_id="tc_1", content="file contents")


@pytest.fixture
def sample_message():
    return Message(role="user", content="Hello", token_count=5)
```

**External service fixtures (for integration tests):**

```python
@pytest.fixture
def config():
    return Config(
        base_url="http://localhost:20128/v1",
        model="test-model",
        api_key="test-key",
        system_prompt="You are a test assistant.",
        temperature=0.0,
        max_tokens=100,
    )
```

## Coverage

**Requirements:** None enforced — no coverage tool configured

**View Coverage:**
- Not applicable — install `pytest-cov` first, then:
  ```bash
  pytest --cov=agent --cov=llm --cov=session --cov=tool --cov=context --cov=config --cov-report=term-missing
  ```

**Current Coverage:** 0% — no tests exist for any module

## Test Types

**Unit Tests:**
- Not present
- Recommended scope: dataclass construction, message validation (`VALID_ROLES`), `ConversationContext` message management, `Session` serialization/deserialization, `ToolRegistry` provider management, `LocalToolProvider` handler dispatch

**Integration Tests:**
- Not present
- Recommended scope: `JSONLSessionStore` save/load/delete (against temp directory), `Agent.run()` loop with mock LLM, `OpenAIClient._call_sdk` message formatting, `MCPToolProvider` against a real or test MCP server

**E2E Tests:**
- Not present
- Not applicable at current project stage — focus on unit + integration coverage first

## Common Patterns

**Async Testing:**
Use `pytest-asyncio` for async test support:

```python
import pytest


@pytest.mark.asyncio
async def test_conversation_context_add_message():
    ctx = ConversationContext(
        count_tokens=lambda t: len(t.split()),
        token_limit=100,
    )
    await ctx.add_user_message("Hello")
    assert len(ctx._messages) == 1
    assert ctx.total_tokens > 0
```

**Error Testing:**

```python
import pytest
from llm.errors import LLMError, LLMConnectionError, LLMResponseError


def test_llm_error_inheritance():
    assert issubclass(LLMConnectionError, LLMError)
    assert issubclass(LLMResponseError, LLMError)


def test_message_invalid_role():
    with pytest.raises(ValueError, match="Invalid role"):
        Message(role="invalid_role", content="test")
```

## Testing Gaps (Priority Order)

| Priority | Gap | Files Affected | Risk |
|----------|-----|----------------|------|
| High | `ConversationContext._maybe_summarize` — complex conditional logic | `context/context.py` | Data loss on summarization failure |
| High | `Agent.run()` — core loop with tool iteration/fallback | `agent/core.py` | Runtime crashes from edge cases |
| High | `JSONLSessionStore.save/load` — JSONL persistence | `session/store.py` | Session data corruption |
| Medium | `OpenAIClient._call_sdk` — API error mapping | `llm/openai_client.py` | Wrong error type on API failure |
| Medium | `Message.__post_init__` — role validation | `context/message.py` | Silent invalid state |
| Medium | `ToolRegistry._register_tools` — namespace collision | `tool/registry.py` | Duplicate tool name crash |
| Low | `Config` field factories — env var parsing | `config.py` | Typed config values failing |
| Low | `LocalToolProvider` built-in handlers | `tool/local_provider.py` | File I/O failures |

---

*Testing analysis: 2026-07-25*
