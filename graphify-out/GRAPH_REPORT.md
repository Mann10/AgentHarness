# Graph Report - .  (2026-07-24)

## Corpus Check
- cluster-only mode — file stats not available

## Summary
- 97 nodes · 246 edges · 8 communities (7 shown, 1 thin omitted)
- Extraction: 89% EXTRACTED · 11% INFERRED · 0% AMBIGUOUS · INFERRED: 26 edges (avg confidence: 0.5)
- Token cost: 0 input · 0 output

## Graph Freshness
- Built from commit: `53f128d7`
- Run `git rev-parse HEAD` and compare to check if the graph is stale.
- Run `graphify update .` after code changes (no API cost).

## Community Hubs (Navigation)
- Tool
- ToolRegistry
- ConversationContext
- LocalToolProvider
- tool/__init__.py
- graphify.js

## God Nodes (most connected - your core abstractions)
1. `ConversationContext` - 22 edges
2. `Tool` - 21 edges
3. `ToolRegistry` - 19 edges
4. `OpenAIClient` - 17 edges
5. `BaseLLMClient` - 14 edges
6. `MCPToolProvider` - 14 edges
7. `Message` - 13 edges
8. `LocalToolProvider` - 13 edges
9. `ToolResult` - 12 edges
10. `LLMResponse` - 11 edges

## Surprising Connections (you probably didn't know these)
- `BaseLLMClient` --uses--> `ConversationContext`  [INFERRED]
  llm/base.py → context/context.py
- `OpenAIClient` --uses--> `ConversationContext`  [INFERRED]
  llm/openai_client.py → context/context.py
- `OpenAIClient` --uses--> `ToolCall`  [INFERRED]
  llm/openai_client.py → tool/models.py
- `BaseLLMClient` --uses--> `Config`  [INFERRED]
  llm/base.py → config.py
- `OpenAIClient` --uses--> `Config`  [INFERRED]
  llm/openai_client.py → config.py

## Import Cycles
- None detected.

## Communities (8 total, 1 thin omitted)

### Community 0 - "Tool"
Cohesion: 0.22
Nodes (10): ABC, Config, Exception, BaseLLMClient, LLMConnectionError, LLMError, LLMResponseError, OpenAIClient (+2 more)

### Community 1 - "ToolRegistry"
Cohesion: 0.13
Nodes (4): Protocol, ToolProvider, _summarize_args(), ToolRegistry

### Community 2 - "ConversationContext"
Cohesion: 0.28
Nodes (3): ConversationContext, Message, ToolCall

### Community 3 - "LocalToolProvider"
Cohesion: 0.22
Nodes (8): _arg_summary(), main(), _list_dir(), LocalToolProvider, _read_file(), register_builtin_tools(), _write_file(), ToolResult

### Community 4 - "tool/__init__.py"
Cohesion: 0.24
Nodes (3): MCPConfig, MCPServerConfig, MCPToolProvider

## Knowledge Gaps
- **1 thin communities (<3 nodes) omitted from report** — run `graphify query` to explore isolated nodes.

## Suggested Questions
_Questions this graph is uniquely positioned to answer:_

- **Why does `Tool` connect `Tool` to `ToolRegistry`, `ConversationContext`, `LocalToolProvider`, `tool/__init__.py`?**
  _High betweenness centrality (0.223) - this node is a cross-community bridge._
- **Why does `ToolRegistry` connect `ToolRegistry` to `Tool`, `LocalToolProvider`, `tool/__init__.py`?**
  _High betweenness centrality (0.181) - this node is a cross-community bridge._
- **Why does `ConversationContext` connect `ConversationContext` to `Tool`, `LocalToolProvider`?**
  _High betweenness centrality (0.162) - this node is a cross-community bridge._
- **Are the 4 inferred relationships involving `ConversationContext` (e.g. with `Message` and `ToolCall`) actually correct?**
  _`ConversationContext` has 4 INFERRED edges - model-reasoned connections that need verification._
- **Are the 5 inferred relationships involving `Tool` (e.g. with `BaseLLMClient` and `OpenAIClient`) actually correct?**
  _`Tool` has 5 INFERRED edges - model-reasoned connections that need verification._
- **Are the 4 inferred relationships involving `ToolRegistry` (e.g. with `MCPToolProvider` and `Tool`) actually correct?**
  _`ToolRegistry` has 4 INFERRED edges - model-reasoned connections that need verification._
- **Are the 8 inferred relationships involving `OpenAIClient` (e.g. with `Config` and `ConversationContext`) actually correct?**
  _`OpenAIClient` has 8 INFERRED edges - model-reasoned connections that need verification._