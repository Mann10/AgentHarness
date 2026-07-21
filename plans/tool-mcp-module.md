# Tool & MCP Module

## Goal
Introduce a `tool/` package and MCP integration layer that enables the agent harness to discover and call external tools via the Model Context Protocol, with `ToolRegistry` serving as both registry and dispatcher.

## Files to Create

| File | Contents |
|---|---|
| `tool/__init__.py` | Public exports |
| `tool/models.py` | `Tool`, `ToolCall`, `ToolResult`, `LLMResponse` dataclasses |
| `tool/registry.py` | `ToolRegistry` — aggregate, route, lifecycle, depth-limit |
| `tool/mcp_provider.py` | `MCPToolProvider` — wraps `mcp` SDK `ClientSession` (stdio + HTTP) |
| `tool/config.py` | `MCPServerConfig`, `MCPConfig` dataclasses |
| `mcp_servers.json` | External config file listing MCP server definitions |

## Files to Modify

| File | Changes |
|---|---|
| `config.py` | Add `mcp_config_path: str` field (default `"mcp_servers.json"`) |
| `context/message.py` | Add `tool` role, `tool_calls`, `tool_call_id` fields |
| `context/context.py` | Add `add_tool_message()`, `add_assistant_tool_message()`; update `to_llm_messages()` for tool call/result serialization |
| `llm/base.py` | `chat()` accepts `tools: list[Tool] \| None`; return type → `LLMResponse`; convert to async |
| `llm/openai_client.py` | Pass `tools` param to SDK; parse `tool_calls` from response; convert to async |
| `main.py` | Async REPL with tool-calling loop, multi-tool support, depth limit |
| `requirements.txt` | Add `mcp>=1.27,<2` |

## Design Details

### 1. `tool/models.py`

```python
@dataclass
class Tool:
    name: str
    description: str
    input_schema: dict

@dataclass
class ToolCall:
    id: str
    name: str
    arguments: dict

@dataclass
class ToolResult:
    tool_call_id: str
    content: str

@dataclass
class LLMResponse:
    content: str | None
    tool_calls: list[ToolCall] | None
```

### 2. `tool/config.py`

```python
@dataclass
class MCPServerConfig:
    name: str
    command: str | None = None
    args: list[str] | None = None
    env: dict[str, str] | None = None
    url: str | None = None
    headers: dict[str, str] | None = None
    namespace: str | None = None

@dataclass
class MCPConfig:
    servers: list[MCPServerConfig]
```

`mcp_servers.json` format:
```json
{
  "mcpServers": [
    {
      "name": "filesystem",
      "command": "npx",
      "args": ["-y", "@modelcontextprotocol/server-filesystem", "C:\\path"],
      "namespace": "fs"
    },
    {
      "name": "github",
      "command": "npx",
      "args": ["-y", "@modelcontextprotocol/server-github"],
      "env": { "GITHUB_TOKEN": "..." }
    },
    {
      "name": "weather-remote",
      "url": "https://mcp.example.com/weather",
      "headers": { "Authorization": "Bearer ..." }
    }
  ]
}
```

### 3. `tool/registry.py` — ToolRegistry

**State:**

| Field | Type | Purpose |
|---|---|---|
| `_providers` | `dict[str, ToolProvider]` | Provider name → provider instance |
| `_tool_map` | `dict[str, str]` | LLM-facing tool name → provider name (routing) |
| `_provider_tools` | `dict[str, list[Tool]]` | Provider name → its tools (for re-registration) |
| `_namespace_map` | `dict[str, str \| None]` | Provider name → namespace prefix |

**Key methods:**

```python
async def start(self) -> None:
    """Initialize all providers: spawn subprocesses, handshake, discover tools."""

async def shutdown(self) -> None:
    """Gracefully terminate all providers."""

def list_tools(self) -> list[Tool]:
    """Aggregate tools from all providers.
    If a provider has a namespace, prepend it to tool names.
    LLM sees fs_read_file; routing strips it back to read_file.
    """

async def call_tool(self, name: str, arguments: dict) -> ToolResult:
    """1. Resolve provider from _tool_map
       2. Strip namespace if applicable -> original tool name
       3. Delegate to provider.call_tool(original_name, arguments)
       4. Return ToolResult
    """

def add_provider(self, name: str, provider, namespace: str | None = None) -> None: ...

def remove_provider(self, name: str) -> None: ...
```

**Namespace handling:**
- When a provider has `namespace="fs"` and its server exposes `read_file`:
  - `list_tools()` returns `Tool(name="fs_read_file", ...)`
  - `call_tool("fs_read_file", args)` strips `fs_` -> `read_file` -> routes to filesystem provider
- When a provider has no namespace, tool names pass through unchanged
- If a collision is detected at registration time (two providers both expose `read_file` with no namespace), raise a clear error telling the user to add a namespace

### 4. `tool/mcp_provider.py` — MCPToolProvider

```python
class MCPToolProvider:
    def __init__(self, config: MCPServerConfig): ...

    async def start(self) -> None:
        if config.command:  # stdio transport
            params = StdioServerParameters(command=config.command, args=config.args, env=config.env)
            read, write = stdio_client(params)
        elif config.url:    # Streamable HTTP
            read, write, _ = streamable_http_client(config.url, headers=config.headers)
        self._session = ClientSession(read, write)
        await self._session.initialize()

    async def shutdown(self) -> None:
        await self._session.__aexit__(None, None, None)

    async def fetch_tools(self) -> list[Tool]:
        response = await self._session.list_tools()
        return [Tool(name=t.name, description=t.description or "", input_schema=t.inputSchema) for t in response.tools]

    async def call_tool(self, name: str, arguments: dict) -> ToolResult:
        result = await self._session.call_tool(name, arguments=arguments)
        text = extract_text(result.content)
        return ToolResult(tool_call_id=name, content=text)
```

### 5. `context/message.py` — Extended

```python
VALID_ROLES = frozenset({"system", "user", "assistant", "tool"})

@dataclass
class Message:
    role: str
    content: str
    token_count: int = 0
    tool_calls: list[ToolCall] | None = None    # assistant only
    tool_call_id: str | None = None              # tool only
```

### 6. `context/context.py` — New Methods

```python
def add_tool_message(self, tool_call_id: str, content: str) -> None:
    self.add_message(Message(role="tool", content=content, tool_call_id=tool_call_id))

def add_assistant_tool_message(self, content: str | None, tool_calls: list[ToolCall]) -> None:
    msg = Message(role="assistant", content=content or "", tool_calls=tool_calls)
    tc_str = json.dumps([asdict(tc) for tc in tool_calls])
    msg.token_count = self._count_tokens((content or "") + tc_str)
    self._messages.append(msg)
    self.total_tokens += msg.token_count
```

`to_llm_messages()` serializes `tool_calls` into OpenAI's format:
```python
def to_llm_messages(self) -> list[dict]:
    result = []
    for m in self._messages:
        d = {"role": m.role, "content": m.content}
        if m.tool_calls:
            d["tool_calls"] = [
                {"id": tc.id, "type": "function",
                 "function": {"name": tc.name, "arguments": json.dumps(tc.arguments)}}
                for tc in m.tool_calls
            ]
        if m.tool_call_id:
            d["tool_call_id"] = m.tool_call_id
        result.append(d)
    return result
```

### 7. `llm/base.py` — Updated Interface (async)

```python
class BaseLLMClient(ABC):
    @abstractmethod
    async def chat(self, context: ConversationContext, *, tools: list[Tool] | None = None, **kwargs) -> LLMResponse: ...

    @abstractmethod
    async def chat_from_messages(self, messages: list[dict], *, tools: list[dict] | None = None, **kwargs) -> LLMResponse: ...
```

### 8. `llm/openai_client.py` — Async + Tool Support

```python
class OpenAIClient(BaseLLMClient):
    async def chat(self, context, *, tools=None, **kwargs):
        return await self._call_sdk(context.to_llm_messages(), tools=tools, **kwargs)

    async def chat_from_messages(self, messages, *, tools=None, **kwargs):
        return await self._call_sdk(messages, tools=tools, **kwargs)

    async def _call_sdk(self, messages, *, tools=None, **kwargs):
        api_tools = None
        if tools:
            api_tools = [
                {"type": "function", "function": {"name": t.name, "description": t.description, "parameters": t.input_schema}}
                for t in tools
            ]
        response = await self._client.chat.completions.create(
            model=self.config.model, messages=messages, tools=api_tools, tool_choice="auto", ...
        )
        msg = response.choices[0].message
        if msg.tool_calls:
            return LLMResponse(
                content=msg.content,
                tool_calls=[ToolCall(id=tc.id, name=tc.function.name, arguments=json.loads(tc.function.arguments)) for tc in msg.tool_calls],
            )
        return LLMResponse(content=msg.content, tool_calls=None)
```

Uses `openai.AsyncOpenAI()` instead of `openai.OpenAI()`.

### 9. `config.py` — Updated

```python
@dataclass
class Config:
    ...
    mcp_config_path: str = field(default_factory=lambda: getenv("MCP_CONFIG_PATH", "mcp_servers.json"))
```

### 10. `main.py` — Async REPL with Tool Loop

```python
MAX_TOOL_ITERATIONS = 15

async def main():
    config = Config()
    client = OpenAIClient(config)
    context = ConversationContext(...)
    registry = ToolRegistry()
    await registry.load_config(config.mcp_config_path)
    await registry.start()

    try:
        while True:
            user_input = input("> ").strip()
            if user_input.lower() in ("exit", "quit"):
                break
            context.add_user_message(user_input)

            tool_iterations = 0
            while tool_iterations < MAX_TOOL_ITERATIONS:
                response = await client.chat(context, tools=registry.list_tools())

                if not response.tool_calls:
                    context.add_assistant_message(response.content)
                    print(response.content)
                    print(f"[{context.total_tokens}/{config.max_tokens} tokens]")
                    break

                context.add_assistant_tool_message(response.content, response.tool_calls)

                tasks = [registry.call_tool(tc.name, tc.arguments) for tc in response.tool_calls]
                results = await asyncio.gather(*tasks, return_exceptions=True)

                for tc, result in zip(response.tool_calls, results):
                    content = str(result) if isinstance(result, Exception) else result.content
                    context.add_tool_message(tc.id, content)

                tool_iterations += 1
            else:
                print("Max tool iterations reached. Forcing text response.")
                response = await client.chat(context)
                context.add_assistant_message(response.content)
                print(response.content)
    finally:
        await registry.shutdown()
```

## Open Questions / Edge Cases

| Concern | Proposal |
|---|---|
| **What if a tool call fails?** | Return error text as tool result; let LLM decide how to handle |
| **What if an MCP server disconnects?** | Mark all its tools as unavailable; remove from `list_tools()`; log warning |
| **Summarization + tool messages?** | Include tool call/result messages in summarization; they count toward token limit |
| **Max tool iterations exceeded?** | Force a final LLM call without tools; the LLM must respond with text |
| **Same tool called multiple times in one response?** | `asyncio.gather` handles this naturally — each call is an independent task |
| **Config file not found?** | Gracefully start with no tools; log a warning |
| **Streaming + tools?** | Defer to a later phase; `stream_chat` remains `NotImplementedError` for now |

## Implementation Order

1. **Phase 1 — Foundation**: Update `requirements.txt`, create `tool/models.py`, `tool/config.py`, extend `Message` and `ConversationContext`
2. **Phase 2 — Async LLM Client**: Convert `BaseLLMClient` and `OpenAIClient` to async; add `tools` parameter; return `LLMResponse`
3. **Phase 3 — MCP Client**: Create `MCPToolProvider` wrapping `mcp` SDK; create `ToolRegistry` with routing and lifecycle
4. **Phase 4 — REPL**: Update `config.py`; rewrite `main.py` as async with tool-calling loop, multi-tool concurrency, depth limit
5. **Phase 5 — Polish**: Edge cases, error recovery, namespace collision errors, logging
