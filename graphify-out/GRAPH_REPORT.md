# Graph Report - AgentHarness  (2026-07-25)

## Corpus Check
- 38 files · ~19,197 words
- Verdict: corpus is large enough that graph structure adds value.

## Summary
- 266 nodes · 464 edges · 22 communities (17 shown, 5 thin omitted)
- Extraction: 94% EXTRACTED · 6% INFERRED · 0% AMBIGUOUS · INFERRED: 26 edges (avg confidence: 0.51)
- Token cost: 0 input · 0 output

## Graph Freshness
- Built from commit: `412a7c0f`
- Run `git rev-parse HEAD` and compare to check if the graph is stale.
- Run `graphify update .` after code changes (no API cost).

## Community Hubs (Navigation)
- Tool
- ToolRegistry
- ConversationContext
- LocalToolProvider
- tool/__init__.py
- graphify.js
- Session
- Design Details
- What You Must Do When Invoked
- Design Details
- Context Layer Module
- opencode.json
- LLM Client Module Refactor
- graphify reference: extra exports and benchmark
- graphify reference: query, path, explain
- graphify reference: add a URL and watch a folder
- graphify reference: commit hook and native CLAUDE.md integration
- graphify reference: incremental update and cluster-only
- graphify reference: GitHub clone and cross-repo merge
- graphify reference: transcribe video and audio
- AGENTS.md
- extraction-spec.md

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
- `BaseLLMClient` --uses--> `ConversationContext`  [INFERRED]
  llm/base.py → context/context.py

## Import Cycles
- None detected.

## Communities (22 total, 5 thin omitted)

### Community 0 - "Tool"
Cohesion: 0.23
Nodes (10): Config, Exception, BaseLLMClient, ABC, LLMConnectionError, LLMError, LLMResponseError, OpenAIClient (+2 more)

### Community 1 - "ToolRegistry"
Cohesion: 0.10
Nodes (8): Protocol, MCPConfig, MCPServerConfig, MCPToolProvider, ToolProvider, ToolResult, _summarize_args(), ToolRegistry

### Community 2 - "ConversationContext"
Cohesion: 0.21
Nodes (3): ConversationContext, Message, ToolCall

### Community 3 - "LocalToolProvider"
Cohesion: 0.21
Nodes (9): _handle_session_cmd(), main(), _make_summarize_fn(), _resolve_session(), _list_dir(), LocalToolProvider, _read_file(), register_builtin_tools() (+1 more)

### Community 4 - "tool/__init__.py"
Cohesion: 0.27
Nodes (3): Agent, _arg_summary(), AgentResult

### Community 6 - "Session"
Cohesion: 0.15
Nodes (6): Path, Session, SessionSummary, JSONLSessionStore, ABC, SessionStore

### Community 7 - "Design Details"
Cohesion: 0.11
Nodes (17): 1. Session Format — JSONL (append-only event log), 2. `session/models.py` — Session, 3. `session/store.py` — JSONLSessionStore, 4. `context/context.py` — Changes, 5. `agent/core.py` — Changes, 6. `main.py` — Full rewrite, 7. `context/message.py` — New Method, 8. `AGENTS.md` — Subagent Rule (+9 more)

### Community 8 - "What You Must Do When Invoked"
Cohesion: 0.08
Nodes (24): For /graphify add and --watch, For /graphify query, For the commit hook and native CLAUDE.md integration, For --update and --cluster-only, /graphify, Honesty Rules, Interpreter guard for subcommands, Part A - Structural extraction for code files (+16 more)

### Community 9 - "Design Details"
Cohesion: 0.11
Nodes (17): 10. `main.py` — Async REPL with Tool Loop, 1. `tool/models.py`, 2. `tool/config.py`, 3. `tool/registry.py` — ToolRegistry, 4. `tool/mcp_provider.py` — MCPToolProvider, 5. `context/message.py` — Extended, 6. `context/context.py` — New Methods, 7. `llm/base.py` — Updated Interface (async) (+9 more)

### Community 10 - "Context Layer Module"
Cohesion: 0.15
Nodes (12): BaseLLMClient changes (`llm/base.py`), Context Layer Module, ConversationContext (`context/context.py`), Design Details, Files to Create, Files to Modify, Goal, Implementation Order (+4 more)

### Community 11 - "opencode.json"
Cohesion: 0.50
Nodes (3): plugin, $schema, .opencode/plugins/graphify.js

### Community 15 - "LLM Client Module Refactor"
Cohesion: 0.18
Nodes (10): BaseLLMClient (base.py), Config additions (config.py), Design Details, Error Hierarchy (errors.py), Files to Create, Files to Delete, Files to Modify, Goal (+2 more)

### Community 16 - "graphify reference: extra exports and benchmark"
Cohesion: 0.22
Nodes (8): graphify reference: extra exports and benchmark, Step 6b - Wiki (only if --wiki flag), Step 7 - Neo4j export (only if --neo4j or --neo4j-push flag), Step 7a - FalkorDB export (only if --falkordb or --falkordb-push flag), Step 7b - SVG export (only if --svg flag), Step 7c - GraphML export (only if --graphml flag), Step 7d - MCP server (only if --mcp flag), Step 8 - Token reduction benchmark (only if total_words > 5000)

### Community 18 - "graphify reference: query, path, explain"
Cohesion: 0.33
Nodes (5): For /graphify explain, For /graphify path, graphify reference: query, path, explain, Step 0 — Constrained query expansion (REQUIRED before traversal), Step 1 — Traversal

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
- **93 isolated node(s):** `$schema`, `.opencode/plugins/graphify.js`, `Usage`, `What graphify is for`, `Step 0 - GitHub repos and multi-path merge (only if a URL or several paths)` (+88 more)
  These have ≤1 connection - possible missing edges or undocumented components.
- **5 thin communities (<3 nodes) omitted from report** — run `graphify query` to explore isolated nodes.

## Suggested Questions
_Questions this graph is uniquely positioned to answer:_

- **Why does `Session` connect `Session` to `ConversationContext`, `LocalToolProvider`, `tool/__init__.py`?**
  _High betweenness centrality (0.059) - this node is a cross-community bridge._
- **Why does `ToolRegistry` connect `ToolRegistry` to `LocalToolProvider`, `tool/__init__.py`?**
  _High betweenness centrality (0.052) - this node is a cross-community bridge._
- **Why does `ConversationContext` connect `ConversationContext` to `Tool`, `LocalToolProvider`, `tool/__init__.py`, `Session`?**
  _High betweenness centrality (0.050) - this node is a cross-community bridge._
- **Are the 6 inferred relationships involving `ConversationContext` (e.g. with `Agent` and `Message`) actually correct?**
  _`ConversationContext` has 6 INFERRED edges - model-reasoned connections that need verification._
- **Are the 5 inferred relationships involving `Session` (e.g. with `Agent` and `ConversationContext`) actually correct?**
  _`Session` has 5 INFERRED edges - model-reasoned connections that need verification._
- **Are the 2 inferred relationships involving `ToolRegistry` (e.g. with `Agent` and `MCPToolProvider`) actually correct?**
  _`ToolRegistry` has 2 INFERRED edges - model-reasoned connections that need verification._
- **Are the 5 inferred relationships involving `OpenAIClient` (e.g. with `Config` and `ConversationContext`) actually correct?**
  _`OpenAIClient` has 5 INFERRED edges - model-reasoned connections that need verification._