---
type: community
cohesion: 0.22
members: 23
---

# OpenAIClient

**Cohesion:** 0.22 - loosely connected
**Members:** 23 nodes

## Members
- [[.__init__()_1]] - code - llm/base.py
- [[.__init__()_2]] - code - llm/openai_client.py
- [[._call_sdk()]] - code - llm/openai_client.py
- [[.chat()]] - code - llm/base.py
- [[.chat()_1]] - code - llm/openai_client.py
- [[.chat_from_messages()]] - code - llm/base.py
- [[.chat_from_messages()_1]] - code - llm/openai_client.py
- [[.count_tokens()]] - code - llm/base.py
- [[.stream_chat()]] - code - llm/base.py
- [[ABC]] - code
- [[BaseLLMClient]] - code - llm/base.py
- [[Config]] - code - config.py
- [[Exception]] - code
- [[LLMConnectionError]] - code - llm/errors.py
- [[LLMError]] - code - llm/errors.py
- [[LLMResponse]] - code - tool/models.py
- [[LLMResponseError]] - code - llm/errors.py
- [[OpenAIClient]] - code - llm/openai_client.py
- [[base.py]] - code - llm/base.py
- [[config.py]] - code - config.py
- [[errors.py]] - code - llm/errors.py
- [[llm__init__.py]] - code - llm/__init__.py
- [[openai_client.py]] - code - llm/openai_client.py

## Live Query (requires Dataview plugin)

```dataview
TABLE source_file, type FROM #community/OpenAIClient
SORT file.name ASC
```

## Connections to other communities
- 16 edges to [[_COMMUNITY_ConversationContext]]
- 11 edges to [[_COMMUNITY_Tool]]
- 1 edge to [[_COMMUNITY_tool__init__.py]]

## Top bridge nodes
- [[OpenAIClient]] - degree 17, connects to 2 communities
- [[BaseLLMClient]] - degree 14, connects to 2 communities
- [[openai_client.py]] - degree 14, connects to 2 communities
- [[LLMResponse]] - degree 11, connects to 2 communities
- [[base.py]] - degree 10, connects to 2 communities