# Graph Report - AgentHarness  (2026-07-25)

## Corpus Check
- 23 files · ~4,688 words
- Verdict: corpus is large enough that graph structure adds value.

## Summary
- 144 nodes · 366 edges · 10 communities (5 shown, 5 thin omitted)
- Extraction: 91% EXTRACTED · 9% INFERRED · 0% AMBIGUOUS · INFERRED: 33 edges (avg confidence: 0.51)
- Token cost: 0 input · 0 output

## Graph Freshness
- Built from commit: `4bffaa65`
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
- ToolProvider
- ToolResult

## God Nodes (most connected - your core abstractions)
1. `ConversationContext` - 36 edges
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
- `BaseLLMClient` --uses--> `ConversationContext`  [INFERRED]
  llm/base.py → context/context.py

## Import Cycles
- None detected.

## Communities (10 total, 5 thin omitted)

### Community 0 - "Session"
Cohesion: 0.15
Nodes (6): Path, Session, SessionSummary, JSONLSessionStore, ABC, SessionStore

### Community 2 - "Tool"
Cohesion: 0.18
Nodes (14): Config, Exception, BaseLLMClient, ABC, LLMConnectionError, LLMError, LLMResponseError, OpenAIClient (+6 more)

### Community 3 - "ConversationContext"
Cohesion: 0.16
Nodes (10): ConversationContext, Message, test_no_summarize_fn_does_nothing(), test_summarization_fires_at_threshold(), test_summarization_keeps_recent_exchanges(), test_summarization_preserves_system_messages(), test_summarization_skips_when_below_threshold(), test_summarization_soft_degrade_on_failure() (+2 more)

### Community 4 - "Agent"
Cohesion: 0.27
Nodes (3): Agent, _arg_summary(), AgentResult

### Community 5 - "LocalToolProvider"
Cohesion: 0.27
Nodes (5): _list_dir(), LocalToolProvider, _read_file(), register_builtin_tools(), _write_file()

## Knowledge Gaps
- **5 thin communities (<3 nodes) omitted from report** — run `graphify query` to explore isolated nodes.

## Suggested Questions
_Questions this graph is uniquely positioned to answer:_

- **Why does `ConversationContext` connect `ConversationContext` to `Session`, `Tool`, `Agent`?**
  _High betweenness centrality (0.274) - this node is a cross-community bridge._
- **Why does `Session` connect `Session` to `Tool`, `ConversationContext`, `Agent`?**
  _High betweenness centrality (0.218) - this node is a cross-community bridge._
- **Why does `ToolRegistry` connect `ToolRegistry` to `tool/__init__.py`, `Tool`, `Agent`, `OpenAIClient`, `ToolProvider`?**
  _High betweenness centrality (0.191) - this node is a cross-community bridge._
- **Are the 6 inferred relationships involving `ConversationContext` (e.g. with `Agent` and `Message`) actually correct?**
  _`ConversationContext` has 6 INFERRED edges - model-reasoned connections that need verification._
- **Are the 5 inferred relationships involving `Session` (e.g. with `Agent` and `ConversationContext`) actually correct?**
  _`Session` has 5 INFERRED edges - model-reasoned connections that need verification._
- **Are the 2 inferred relationships involving `ToolRegistry` (e.g. with `Agent` and `MCPToolProvider`) actually correct?**
  _`ToolRegistry` has 2 INFERRED edges - model-reasoned connections that need verification._
- **Are the 5 inferred relationships involving `OpenAIClient` (e.g. with `Config` and `ConversationContext`) actually correct?**
  _`OpenAIClient` has 5 INFERRED edges - model-reasoned connections that need verification._