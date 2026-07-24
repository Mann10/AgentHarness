---
type: community
cohesion: 0.25
members: 15
---

# Tool

**Cohesion:** 0.25 - loosely connected
**Members:** 15 nodes

## Members
- [[.__init__()_3]] - code - tool/local_provider.py
- [[.add_tool()]] - code - tool/local_provider.py
- [[.fetch_tools()]] - code - tool/local_provider.py
- [[.shutdown()]] - code - tool/local_provider.py
- [[.start()]] - code - tool/local_provider.py
- [[LocalToolProvider]] - code - tool/local_provider.py
- [[Tool]] - code - tool/models.py
- [[_arg_summary()]] - code - main.py
- [[_list_dir()]] - code - tool/local_provider.py
- [[_read_file()]] - code - tool/local_provider.py
- [[_write_file()]] - code - tool/local_provider.py
- [[local_provider.py]] - code - tool/local_provider.py
- [[main()]] - code - main.py
- [[main.py]] - code - main.py
- [[register_builtin_tools()]] - code - tool/local_provider.py

## Live Query (requires Dataview plugin)

```dataview
TABLE source_file, type FROM #community/Tool
SORT file.name ASC
```

## Connections to other communities
- 12 edges to [[_COMMUNITY_tool__init__.py]]
- 11 edges to [[_COMMUNITY_OpenAIClient]]
- 6 edges to [[_COMMUNITY_ToolRegistry]]
- 5 edges to [[_COMMUNITY_ConversationContext]]

## Top bridge nodes
- [[Tool]] - degree 21, connects to 4 communities
- [[main.py]] - degree 10, connects to 4 communities
- [[main()]] - degree 8, connects to 3 communities
- [[local_provider.py]] - degree 9, connects to 2 communities
- [[LocalToolProvider]] - degree 13, connects to 1 community