---
type: community
cohesion: 0.15
members: 17
---

# ToolRegistry

**Cohesion:** 0.15 - loosely connected
**Members:** 17 nodes

## Members
- [[.__init__()_5]] - code - tool/registry.py
- [[._register_tools()]] - code - tool/registry.py
- [[._resolve_with_namespace()]] - code - tool/registry.py
- [[.add_provider()]] - code - tool/registry.py
- [[.call_tool()_3]] - code - tool/registry.py
- [[.fetch_tools()_2]] - code - tool/models.py
- [[.list_tools()]] - code - tool/registry.py
- [[.provider_count()]] - code - tool/registry.py
- [[.shutdown()_2]] - code - tool/models.py
- [[.shutdown()_3]] - code - tool/registry.py
- [[.start()_2]] - code - tool/models.py
- [[.start()_3]] - code - tool/registry.py
- [[.tool_count()]] - code - tool/registry.py
- [[Protocol]] - code
- [[ToolProvider]] - code - tool/models.py
- [[ToolRegistry]] - code - tool/registry.py
- [[_summarize_args()]] - code - tool/registry.py

## Live Query (requires Dataview plugin)

```dataview
TABLE source_file, type FROM #community/ToolRegistry
SORT file.name ASC
```

## Connections to other communities
- 10 edges to [[_COMMUNITY_tool__init__.py]]
- 6 edges to [[_COMMUNITY_Tool]]
- 1 edge to [[_COMMUNITY_ConversationContext]]

## Top bridge nodes
- [[ToolRegistry]] - degree 19, connects to 2 communities
- [[ToolProvider]] - degree 10, connects to 2 communities
- [[.call_tool()_3]] - degree 5, connects to 1 community
- [[.list_tools()]] - degree 3, connects to 1 community
- [[._register_tools()]] - degree 3, connects to 1 community