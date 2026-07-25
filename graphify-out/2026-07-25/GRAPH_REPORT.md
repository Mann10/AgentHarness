# Graph Report - AgentHarness  (2026-07-24)

## Corpus Check
- 132 files · ~22,095 words
- Verdict: corpus is large enough that graph structure adds value.

## Summary
- 515 nodes · 879 edges · 56 communities (26 shown, 30 thin omitted)
- Extraction: 97% EXTRACTED · 3% INFERRED · 0% AMBIGUOUS · INFERRED: 30 edges (avg confidence: 0.5)
- Token cost: 0 input · 0 output

## Graph Freshness
- Built from commit: `8d6e1c30`
- Run `git rev-parse HEAD` and compare to check if the graph is stale.
- Run `graphify update .` after code changes (no API cost).

## Community Hubs (Navigation)
- Tool
- ToolRegistry
- ConversationContext
- LocalToolProvider
- tool/__init__.py
- graphify.js
- .obsidian/app.json
- vault/.obsidian/app.json
- What You Must Do When Invoked
- Design Details
- Context Layer Module
- _COMMUNITY_ToolRegistry.md
- .call_tool()_3.md
- registry.py.md
- MCPServerConfig.md
- LLM Client Module Refactor
- graphify reference: extra exports and benchmark
- ToolRegistry.md
- graphify reference: query, path, explain
- ._register_tools().md
- ConversationContext
- OpenAIClient
- Tool
- tool/__init__.py
- ToolRegistry
- graphify reference: add a URL and watch a folder
- graphify reference: commit hook and native CLAUDE.md integration
- graphify reference: incremental update and cluster-only
- graphify reference: GitHub clone and cross-repo merge
- graphify reference: transcribe video and audio
- config.py.md
- Exception.md
- models.py.md
- .shutdown()_3.md
- .tool_count().md
- tool__init__.py.md
- AGENTS.md
- extraction-spec.md
- .add_message
- .add_tool_message
- .add_user_message
- context/__init__.py
- ConversationContext
- .fetch_tools
- .fetch_tools
- local_provider.py
- LocalToolProvider
- .__post_init__
- Protocol
- register_builtin_tools
- .shutdown
- .shutdown
- .start
- .to_llm_messages
- ToolCall
- ToolResult

## God Nodes (most connected - your core abstractions)
1. `ConversationContext` - 26 edges
2. `ToolRegistry` - 22 edges
3. `Tool` - 21 edges
4. `BaseLLMClient` - 17 edges
5. `OpenAIClient` - 17 edges
6. `MCPToolProvider` - 14 edges
7. `Agent` - 13 edges
8. `Message` - 13 edges
9. `LocalToolProvider` - 13 edges
10. `ToolResult` - 12 edges

## Surprising Connections (you probably didn't know these)
- `Agent` --uses--> `ToolRegistry`  [INFERRED]
  agent/core.py → tool/registry.py
- `BaseLLMClient` --uses--> `Tool`  [INFERRED]
  llm/base.py → tool/models.py
- `OpenAIClient` --uses--> `Tool`  [INFERRED]
  llm/openai_client.py → tool/models.py
- `Agent` --uses--> `ConversationContext`  [INFERRED]
  agent/core.py → context/context.py
- `Agent` --uses--> `BaseLLMClient`  [INFERRED]
  agent/core.py → llm/base.py

## Import Cycles
- None detected.

## Communities (56 total, 30 thin omitted)

### Community 0 - "Tool"
Cohesion: 0.10
Nodes (16): ABC, Agent, _arg_summary(), AgentResult, Config, ConversationContext, Message, Exception (+8 more)

### Community 1 - "ToolRegistry"
Cohesion: 0.09
Nodes (14): Protocol, MCPConfig, MCPServerConfig, _list_dir(), LocalToolProvider, _read_file(), register_builtin_tools(), _write_file() (+6 more)

### Community 2 - "ConversationContext"
Cohesion: 0.08
Nodes (16): ABC, Connections, base.py, Connections, BaseLLMClient, Connections, Connections, Connections (+8 more)

### Community 3 - "LocalToolProvider"
Cohesion: 0.08
Nodes (23): _arg_summary(), Connections, Config, Connections, Connections, errors.py, Connections, Connections (+15 more)

### Community 4 - "tool/__init__.py"
Cohesion: 0.12
Nodes (11): Connections, Connections, Connections, context.py, Connections, Connections, Connections, Message (+3 more)

### Community 6 - ".obsidian/app.json"
Cohesion: 0.10
Nodes (10): Connections, Connections, Connections, Connections, Connections, MCPToolProvider, Connections, Connections (+2 more)

### Community 7 - "vault/.obsidian/app.json"
Cohesion: 0.13
Nodes (11): Connections, Connections, Connections, Connections, _list_dir(), Connections, _read_file(), Connections (+3 more)

### Community 8 - "What You Must Do When Invoked"
Cohesion: 0.08
Nodes (24): For /graphify add and --watch, For /graphify query, For the commit hook and native CLAUDE.md integration, For --update and --cluster-only, /graphify, Honesty Rules, Interpreter guard for subcommands, Part A - Structural extraction for code files (+16 more)

### Community 9 - "Design Details"
Cohesion: 0.11
Nodes (17): 10. `main.py` — Async REPL with Tool Loop, 1. `tool/models.py`, 2. `tool/config.py`, 3. `tool/registry.py` — ToolRegistry, 4. `tool/mcp_provider.py` — MCPToolProvider, 5. `context/message.py` — Extended, 6. `context/context.py` — New Methods, 7. `llm/base.py` — Updated Interface (async) (+9 more)

### Community 10 - "Context Layer Module"
Cohesion: 0.15
Nodes (12): BaseLLMClient changes (`llm/base.py`), Context Layer Module, ConversationContext (`context/context.py`), Design Details, Files to Create, Files to Modify, Goal, Implementation Order (+4 more)

### Community 11 - "_COMMUNITY_ToolRegistry.md"
Cohesion: 0.22
Nodes (4): Connections, Connections, Connections, ToolProvider

### Community 12 - ".call_tool()_3.md"
Cohesion: 0.17
Nodes (5): Connections, Connections, Connections, Connections, _summarize_args()

### Community 13 - "registry.py.md"
Cohesion: 0.18
Nodes (6): Connections, Connections, Connections, MCPConfig, Connections, registry.py

### Community 14 - "MCPServerConfig.md"
Cohesion: 0.17
Nodes (7): Connections, Connections, mcp_provider.py, Connections, MCPServerConfig, Connections, tool/config.py

### Community 15 - "LLM Client Module Refactor"
Cohesion: 0.18
Nodes (10): BaseLLMClient (base.py), Config additions (config.py), Design Details, Error Hierarchy (errors.py), Files to Create, Files to Delete, Files to Modify, Goal (+2 more)

### Community 16 - "graphify reference: extra exports and benchmark"
Cohesion: 0.22
Nodes (8): graphify reference: extra exports and benchmark, Step 6b - Wiki (only if --wiki flag), Step 7 - Neo4j export (only if --neo4j or --neo4j-push flag), Step 7a - FalkorDB export (only if --falkordb or --falkordb-push flag), Step 7b - SVG export (only if --svg flag), Step 7c - GraphML export (only if --graphml flag), Step 7d - MCP server (only if --mcp flag), Step 8 - Token reduction benchmark (only if total_words > 5000)

### Community 17 - "ToolRegistry.md"
Cohesion: 0.22
Nodes (4): Connections, Connections, Connections, ToolRegistry

### Community 18 - "graphify reference: query, path, explain"
Cohesion: 0.33
Nodes (5): For /graphify explain, For /graphify path, graphify reference: query, path, explain, Step 0 — Constrained query expansion (REQUIRED before traversal), Step 1 — Traversal

### Community 20 - "ConversationContext"
Cohesion: 0.40
Nodes (5): Connections to other communities, ConversationContext, Live Query (requires Dataview plugin), Members, Top bridge nodes

### Community 21 - "OpenAIClient"
Cohesion: 0.40
Nodes (5): Connections to other communities, Live Query (requires Dataview plugin), Members, OpenAIClient, Top bridge nodes

### Community 22 - "Tool"
Cohesion: 0.40
Nodes (5): Connections to other communities, Live Query (requires Dataview plugin), Members, Tool, Top bridge nodes

### Community 23 - "tool/__init__.py"
Cohesion: 0.40
Nodes (5): Connections to other communities, Live Query (requires Dataview plugin), Members, tool/__init__.py, Top bridge nodes

### Community 24 - "ToolRegistry"
Cohesion: 0.40
Nodes (5): Connections to other communities, Live Query (requires Dataview plugin), Members, ToolRegistry, Top bridge nodes

### Community 25 - "graphify reference: add a URL and watch a folder"
Cohesion: 0.50
Nodes (3): For /graphify add, For --watch, graphify reference: add a URL and watch a folder

### Community 26 - "graphify reference: commit hook and native CLAUDE.md integration"
Cohesion: 0.50
Nodes (3): For git commit hook, For native CLAUDE.md integration, graphify reference: commit hook and native CLAUDE.md integration

### Community 27 - "graphify reference: incremental update and cluster-only"
Cohesion: 0.50
Nodes (3): For --cluster-only, For --update (incremental re-extraction), graphify reference: incremental update and cluster-only

## Knowledge Gaps
- **187 isolated node(s):** `Usage`, `What graphify is for`, `Step 0 - GitHub repos and multi-path merge (only if a URL or several paths)`, `Step 1 - Ensure graphify is installed`, `Step 2 - Detect files` (+182 more)
  These have ≤1 connection - possible missing edges or undocumented components.
- **30 thin communities (<3 nodes) omitted from report** — run `graphify query` to explore isolated nodes.

## Suggested Questions
_Questions this graph is uniquely positioned to answer:_

- **Why does `ToolRegistry` connect `ToolRegistry` to `Tool`?**
  _High betweenness centrality (0.080) - this node is a cross-community bridge._
- **Why does `OpenAIClient` connect `Tool` to `ToolRegistry`?**
  _High betweenness centrality (0.032) - this node is a cross-community bridge._
- **Are the 5 inferred relationships involving `ConversationContext` (e.g. with `Agent` and `Message`) actually correct?**
  _`ConversationContext` has 5 INFERRED edges - model-reasoned connections that need verification._
- **Are the 5 inferred relationships involving `ToolRegistry` (e.g. with `Agent` and `MCPToolProvider`) actually correct?**
  _`ToolRegistry` has 5 INFERRED edges - model-reasoned connections that need verification._
- **Are the 5 inferred relationships involving `Tool` (e.g. with `BaseLLMClient` and `OpenAIClient`) actually correct?**
  _`Tool` has 5 INFERRED edges - model-reasoned connections that need verification._
- **Are the 6 inferred relationships involving `BaseLLMClient` (e.g. with `Agent` and `Config`) actually correct?**
  _`BaseLLMClient` has 6 INFERRED edges - model-reasoned connections that need verification._
- **Are the 8 inferred relationships involving `OpenAIClient` (e.g. with `Config` and `ConversationContext`) actually correct?**
  _`OpenAIClient` has 8 INFERRED edges - model-reasoned connections that need verification._