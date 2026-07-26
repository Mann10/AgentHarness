# Graph Report - AgentHarness  (2026-07-25)

## Corpus Check
- 35 files · ~6,467 words
- Verdict: corpus is large enough that graph structure adds value.

## Summary
- 228 nodes · 562 edges · 8 communities
- Extraction: 92% EXTRACTED · 8% INFERRED · 0% AMBIGUOUS · INFERRED: 46 edges (avg confidence: 0.53)
- Token cost: 0 input · 0 output

## Graph Freshness
- Built from commit: `7454c2a1`
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
1. `ConversationContext` - 36 edges
2. `Session` - 24 edges
3. `QueueManager` - 23 edges
4. `ToolRegistry` - 22 edges
5. `Job` - 21 edges
6. `OpenAIClient` - 20 edges
7. `AgentHarnessTUI` - 20 edges
8. `SQLiteJobStore` - 19 edges
9. `Agent` - 17 edges
10. `Tool` - 17 edges

## Surprising Connections (you probably didn't know these)
- `Agent` --uses--> `ConversationContext`  [INFERRED]
  agent/core.py → context/context.py
- `Agent` --uses--> `BaseLLMClient`  [INFERRED]
  agent/core.py → llm/base.py
- `BaseLLMClient` --uses--> `Config`  [INFERRED]
  llm/base.py → config.py
- `BaseLLMClient` --uses--> `ConversationContext`  [INFERRED]
  llm/base.py → context/context.py
- `OpenAIClient` --uses--> `ConversationContext`  [INFERRED]
  llm/openai_client.py → context/context.py

## Import Cycles
- None detected.

## Communities (8 total, 0 thin omitted)

### Community 0 - "Session"
Cohesion: 0.13
Nodes (6): Path, Session, SessionSummary, JSONLSessionStore, ABC, SessionStore

### Community 1 - "tool/__init__.py"
Cohesion: 0.07
Nodes (14): App, DataTable, Footer, Input, RowSelected, Screen, Submitted, AgentHarnessTUI (+6 more)

### Community 2 - "Tool"
Cohesion: 0.23
Nodes (8): Exception, BaseLLMClient, ABC, LLMConnectionError, LLMError, LLMResponseError, LLMResponse, Tool

### Community 3 - "ConversationContext"
Cohesion: 0.16
Nodes (10): ConversationContext, Message, test_no_summarize_fn_does_nothing(), test_summarization_fires_at_threshold(), test_summarization_keeps_recent_exchanges(), test_summarization_preserves_system_messages(), test_summarization_skips_when_below_threshold(), test_summarization_soft_degrade_on_failure() (+2 more)

### Community 4 - "Agent"
Cohesion: 0.14
Nodes (5): Agent, _arg_summary(), AgentResult, _summarize_args(), ToolRegistry

### Community 5 - "LocalToolProvider"
Cohesion: 0.10
Nodes (11): Protocol, MCPConfig, MCPServerConfig, _list_dir(), LocalToolProvider, _read_file(), register_builtin_tools(), _write_file() (+3 more)

### Community 6 - "ToolRegistry"
Cohesion: 0.13
Nodes (9): Connection, datetime, Enum, QueueManager, Job, JobPriority, JobStatus, SQLiteJobStore (+1 more)

### Community 7 - "OpenAIClient"
Cohesion: 0.37
Nodes (11): Config, OpenAIClient, _handle_session_cmd(), main(), _make_summarize_fn(), _parse_args(), _resolve_session(), run_repl() (+3 more)

## Suggested Questions
_Questions this graph is uniquely positioned to answer:_

- **Why does `AgentHarnessTUI` connect `tool/__init__.py` to `ToolRegistry`, `OpenAIClient`?**
  _High betweenness centrality (0.239) - this node is a cross-community bridge._
- **Why does `QueueManager` connect `ToolRegistry` to `tool/__init__.py`, `OpenAIClient`?**
  _High betweenness centrality (0.184) - this node is a cross-community bridge._
- **Why does `ToolRegistry` connect `Agent` to `LocalToolProvider`, `OpenAIClient`?**
  _High betweenness centrality (0.183) - this node is a cross-community bridge._
- **Are the 6 inferred relationships involving `ConversationContext` (e.g. with `Agent` and `Message`) actually correct?**
  _`ConversationContext` has 6 INFERRED edges - model-reasoned connections that need verification._
- **Are the 2 inferred relationships involving `Session` (e.g. with `ConversationContext` and `Message`) actually correct?**
  _`Session` has 2 INFERRED edges - model-reasoned connections that need verification._
- **Are the 5 inferred relationships involving `QueueManager` (e.g. with `Job` and `JobPriority`) actually correct?**
  _`QueueManager` has 5 INFERRED edges - model-reasoned connections that need verification._
- **Are the 2 inferred relationships involving `ToolRegistry` (e.g. with `Agent` and `MCPToolProvider`) actually correct?**
  _`ToolRegistry` has 2 INFERRED edges - model-reasoned connections that need verification._