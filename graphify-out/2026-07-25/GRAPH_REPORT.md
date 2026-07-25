# Graph Report - .  (2026-07-25)

## Corpus Check
- cluster-only mode — file stats not available

## Summary
- 136 nodes · 350 edges · 8 communities (7 shown, 1 thin omitted)
- Extraction: 93% EXTRACTED · 7% INFERRED · 0% AMBIGUOUS · INFERRED: 26 edges (avg confidence: 0.51)
- Token cost: 0 input · 0 output

## Graph Freshness
- Built from commit: `eeec49eb`
- Run `git rev-parse HEAD` and compare to check if the graph is stale.
- Run `graphify update .` after code changes (no API cost).

## Community Hubs (Navigation)
- Session
- tool/__init__.py
- Tool
- ConversationContext
- Agent
- LocalToolProvider
- ToolRegistry
- OpenAIClient

## God Nodes (most connected - your core abstractions)
1. `ConversationContext` - 28 edges
2. `Session` - 27 edges
3. `ToolRegistry` - 19 edges
4. `OpenAIClient` - 17 edges
5. `Tool` - 17 edges
6. `Agent` - 16 edges
7. `Message` - 15 edges
8. `BaseLLMClient` - 15 edges
9. `JSONLSessionStore` - 15 edges
10. `MCPToolProvider` - 12 edges

## Surprising Connections (you probably didn't know these)
- `Agent` --uses--> `ConversationContext`  [INFERRED]
  agent/core.py → context/context.py
- `Agent` --uses--> `BaseLLMClient`  [INFERRED]
  agent/core.py → llm/base.py
- `Agent` --uses--> `Session`  [INFERRED]
  agent/core.py → session/models.py
- `Agent` --uses--> `ToolRegistry`  [INFERRED]
  agent/core.py → tool/registry.py
- `BaseLLMClient` --uses--> `Config`  [INFERRED]
  llm/base.py → config.py

## Import Cycles
- None detected.

## Communities (8 total, 1 thin omitted)

### Community 0 - "Session"
Cohesion: 0.15
Nodes (6): Path, Session, SessionSummary, JSONLSessionStore, ABC, SessionStore

### Community 1 - "tool/__init__.py"
Cohesion: 0.15
Nodes (6): Protocol, MCPConfig, MCPServerConfig, MCPToolProvider, ToolProvider, ToolResult

### Community 2 - "Tool"
Cohesion: 0.23
Nodes (8): Exception, BaseLLMClient, ABC, LLMConnectionError, LLMError, LLMResponseError, LLMResponse, Tool

### Community 3 - "ConversationContext"
Cohesion: 0.24
Nodes (3): ConversationContext, Message, ToolCall

### Community 4 - "Agent"
Cohesion: 0.27
Nodes (3): Agent, _arg_summary(), AgentResult

### Community 5 - "LocalToolProvider"
Cohesion: 0.24
Nodes (5): _list_dir(), LocalToolProvider, _read_file(), register_builtin_tools(), _write_file()

### Community 7 - "OpenAIClient"
Cohesion: 0.49
Nodes (6): Config, OpenAIClient, _handle_session_cmd(), main(), _make_summarize_fn(), _resolve_session()

## Knowledge Gaps
- **1 thin communities (<3 nodes) omitted from report** — run `graphify query` to explore isolated nodes.

## Suggested Questions
_Questions this graph is uniquely positioned to answer:_

- **Why does `Session` connect `Session` to `ConversationContext`, `Agent`, `OpenAIClient`?**
  _High betweenness centrality (0.228) - this node is a cross-community bridge._
- **Why does `ToolRegistry` connect `ToolRegistry` to `tool/__init__.py`, `Agent`, `OpenAIClient`?**
  _High betweenness centrality (0.202) - this node is a cross-community bridge._
- **Why does `ConversationContext` connect `ConversationContext` to `Session`, `Tool`, `Agent`, `OpenAIClient`?**
  _High betweenness centrality (0.195) - this node is a cross-community bridge._
- **Are the 6 inferred relationships involving `ConversationContext` (e.g. with `Agent` and `Message`) actually correct?**
  _`ConversationContext` has 6 INFERRED edges - model-reasoned connections that need verification._
- **Are the 5 inferred relationships involving `Session` (e.g. with `Agent` and `ConversationContext`) actually correct?**
  _`Session` has 5 INFERRED edges - model-reasoned connections that need verification._
- **Are the 2 inferred relationships involving `ToolRegistry` (e.g. with `Agent` and `MCPToolProvider`) actually correct?**
  _`ToolRegistry` has 2 INFERRED edges - model-reasoned connections that need verification._
- **Are the 5 inferred relationships involving `OpenAIClient` (e.g. with `Config` and `ConversationContext`) actually correct?**
  _`OpenAIClient` has 5 INFERRED edges - model-reasoned connections that need verification._