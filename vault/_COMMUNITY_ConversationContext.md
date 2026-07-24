---
type: community
cohesion: 0.28
members: 17
---

# ConversationContext

**Cohesion:** 0.28 - loosely connected
**Members:** 17 nodes

## Members
- [[.__init__()]] - code - context/context.py
- [[.__post_init__()]] - code - context/message.py
- [[._maybe_summarize()]] - code - context/context.py
- [[.add_assistant_message()]] - code - context/context.py
- [[.add_assistant_tool_message()]] - code - context/context.py
- [[.add_message()]] - code - context/context.py
- [[.add_tool_message()]] - code - context/context.py
- [[.add_user_message()]] - code - context/context.py
- [[.stream_chat()_1]] - code - llm/openai_client.py
- [[.to_llm_messages()]] - code - context/context.py
- [[ConversationContext]] - code - context/context.py
- [[Message]] - code - context/message.py
- [[ToolCall]] - code - tool/models.py
- [[context.py]] - code - context/context.py
- [[context__init__.py]] - code - context/__init__.py
- [[message.py]] - code - context/message.py
- [[models.py]] - code - tool/models.py

## Live Query (requires Dataview plugin)

```dataview
TABLE source_file, type FROM #community/ConversationContext
SORT file.name ASC
```

## Connections to other communities
- 16 edges to [[_COMMUNITY_OpenAIClient]]
- 5 edges to [[_COMMUNITY_Tool]]
- 5 edges to [[_COMMUNITY_tool__init__.py]]
- 1 edge to [[_COMMUNITY_ToolRegistry]]

## Top bridge nodes
- [[models.py]] - degree 13, connects to 4 communities
- [[ConversationContext]] - degree 22, connects to 2 communities
- [[ToolCall]] - degree 10, connects to 2 communities
- [[context.py]] - degree 9, connects to 2 communities
- [[.stream_chat()_1]] - degree 2, connects to 1 community