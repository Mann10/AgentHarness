# Graph Report - .  (2026-07-24)

## Corpus Check
- cluster-only mode — file stats not available

## Summary
- 93 nodes · 248 edges · 5 communities
- Extraction: 90% EXTRACTED · 10% INFERRED · 0% AMBIGUOUS · INFERRED: 26 edges (avg confidence: 0.5)
- Token cost: 0 input · 0 output

## Graph Freshness
- Built from commit: `fe83d22f`
- Run `git rev-parse HEAD` and compare to check if the graph is stale.
- Run `graphify update .` after code changes (no API cost).

## Community Hubs (Navigation)
- OpenAIClient
- ToolRegistry
- tool/__init__.py
- ConversationContext
- Tool

## God Nodes (most connected - your core abstractions)
1. `Tool` - 23 edges
2. `ConversationContext` - 22 edges
3. `ToolRegistry` - 20 edges
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
- `BaseLLMClient` --uses--> `Tool`  [INFERRED]
  llm/base.py → tool/models.py
- `OpenAIClient` --uses--> `Tool`  [INFERRED]
  llm/openai_client.py → tool/models.py
- `OpenAIClient` --uses--> `ToolCall`  [INFERRED]
  llm/openai_client.py → tool/models.py

## Import Cycles
- None detected.

## Communities (5 total, 0 thin omitted)

### Community 0 - "OpenAIClient"
Cohesion: 0.22
Nodes (9): ABC, Config, Exception, BaseLLMClient, LLMConnectionError, LLMError, LLMResponseError, OpenAIClient (+1 more)

### Community 1 - "ToolRegistry"
Cohesion: 0.13
Nodes (4): Protocol, ToolProvider, _summarize_args(), ToolRegistry

### Community 2 - "tool/__init__.py"
Cohesion: 0.24
Nodes (4): MCPConfig, MCPServerConfig, MCPToolProvider, ToolResult

### Community 3 - "ConversationContext"
Cohesion: 0.28
Nodes (3): ConversationContext, Message, ToolCall

### Community 4 - "Tool"
Cohesion: 0.23
Nodes (8): _arg_summary(), main(), _list_dir(), LocalToolProvider, _read_file(), register_builtin_tools(), _write_file(), Tool

## Suggested Questions
_Questions this graph is uniquely positioned to answer:_

- **Why does `Tool` connect `Tool` to `OpenAIClient`, `ToolRegistry`, `tool/__init__.py`, `ConversationContext`?**
  _High betweenness centrality (0.266) - this node is a cross-community bridge._
- **Why does `ToolRegistry` connect `ToolRegistry` to `tool/__init__.py`, `Tool`?**
  _High betweenness centrality (0.194) - this node is a cross-community bridge._
- **Why does `ConversationContext` connect `ConversationContext` to `OpenAIClient`, `Tool`?**
  _High betweenness centrality (0.179) - this node is a cross-community bridge._
- **Are the 5 inferred relationships involving `Tool` (e.g. with `BaseLLMClient` and `OpenAIClient`) actually correct?**
  _`Tool` has 5 INFERRED edges - model-reasoned connections that need verification._
- **Are the 4 inferred relationships involving `ConversationContext` (e.g. with `Message` and `ToolCall`) actually correct?**
  _`ConversationContext` has 4 INFERRED edges - model-reasoned connections that need verification._
- **Are the 4 inferred relationships involving `ToolRegistry` (e.g. with `MCPToolProvider` and `Tool`) actually correct?**
  _`ToolRegistry` has 4 INFERRED edges - model-reasoned connections that need verification._
- **Are the 8 inferred relationships involving `OpenAIClient` (e.g. with `Config` and `ConversationContext`) actually correct?**
  _`OpenAIClient` has 8 INFERRED edges - model-reasoned connections that need verification._