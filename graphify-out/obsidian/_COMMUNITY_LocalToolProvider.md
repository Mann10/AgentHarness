---
type: community
cohesion: 0.22
members: 15
---

# LocalToolProvider

**Cohesion:** 0.22 - loosely connected
**Members:** 15 nodes

## Members
- [[.__init__()_4]] - code - tool/local_provider.py
- [[.add_tool()]] - code - tool/local_provider.py
- [[.call_tool()]] - code - tool/local_provider.py
- [[.fetch_tools()]] - code - tool/local_provider.py
- [[.shutdown()_1]] - code - tool/local_provider.py
- [[.start()_1]] - code - tool/local_provider.py
- [[LocalToolProvider]] - code - tool/local_provider.py
- [[ToolResult]] - code - tool/models.py
- [[_list_dir()]] - code - tool/local_provider.py
- [[_read_file()]] - code - tool/local_provider.py
- [[_write_file()]] - code - tool/local_provider.py
- [[local_provider.py]] - code - tool/local_provider.py
- [[main()]] - code - main.py
- [[main.py]] - code - main.py
- [[register_builtin_tools()]] - code - tool/local_provider.py

## Live Query (requires Dataview plugin)

```dataview
TABLE source_file, type FROM #community/LocalToolProvider
SORT file.name ASC
```

## Connections to other communities
- 8 edges to [[_COMMUNITY_Tool]]
- 8 edges to [[_COMMUNITY_tool__init__.py]]
- 5 edges to [[_COMMUNITY_ConversationContext]]
- 5 edges to [[_COMMUNITY_ToolRegistry]]

## Top bridge nodes
- [[ToolResult]] - degree 12, connects to 3 communities
- [[main.py]] - degree 10, connects to 3 communities
- [[local_provider.py]] - degree 9, connects to 3 communities
- [[main()]] - degree 8, connects to 3 communities
- [[LocalToolProvider]] - degree 13, connects to 2 communities