---
type: community
cohesion: 0.20
members: 20
---

# tool/__init__.py

**Cohesion:** 0.20 - loosely connected
**Members:** 20 nodes

## Members
- [[.__init__()_4]] - code - tool/mcp_provider.py
- [[._start_http()]] - code - tool/mcp_provider.py
- [[._start_stdio()]] - code - tool/mcp_provider.py
- [[.call_tool()]] - code - tool/local_provider.py
- [[.call_tool()_1]] - code - tool/mcp_provider.py
- [[.call_tool()_2]] - code - tool/models.py
- [[.fetch_tools()_1]] - code - tool/mcp_provider.py
- [[.from_dict()]] - code - tool/config.py
- [[.from_file()]] - code - tool/config.py
- [[.load_config()]] - code - tool/registry.py
- [[.shutdown()_1]] - code - tool/mcp_provider.py
- [[.start()_1]] - code - tool/mcp_provider.py
- [[MCPConfig]] - code - tool/config.py
- [[MCPServerConfig]] - code - tool/config.py
- [[MCPToolProvider]] - code - tool/mcp_provider.py
- [[ToolResult]] - code - tool/models.py
- [[mcp_provider.py]] - code - tool/mcp_provider.py
- [[registry.py]] - code - tool/registry.py
- [[tool__init__.py]] - code - tool/__init__.py
- [[toolconfig.py]] - code - tool/config.py

## Live Query (requires Dataview plugin)

```dataview
TABLE source_file, type FROM #community/tool/__init__py
SORT file.name ASC
```

## Connections to other communities
- 12 edges to [[_COMMUNITY_Tool]]
- 10 edges to [[_COMMUNITY_ToolRegistry]]
- 5 edges to [[_COMMUNITY_ConversationContext]]
- 1 edge to [[_COMMUNITY_OpenAIClient]]

## Top bridge nodes
- [[tool__init__.py]] - degree 16, connects to 4 communities
- [[ToolResult]] - degree 12, connects to 3 communities
- [[registry.py]] - degree 11, connects to 3 communities
- [[MCPToolProvider]] - degree 14, connects to 2 communities
- [[mcp_provider.py]] - degree 8, connects to 2 communities