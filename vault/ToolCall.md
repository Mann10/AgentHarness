---
source_file: "tool/models.py"
type: "code"
community: "ConversationContext"
location: "L23"
tags:
  - graphify/code
  - graphify/EXTRACTED
  - community/ConversationContext
---

# ToolCall

## Connections
- [[._call_sdk()]] - `calls` [EXTRACTED]
- [[.add_assistant_tool_message()]] - `references` [EXTRACTED]
- [[ConversationContext]] - `uses` [INFERRED]
- [[Message]] - `uses` [INFERRED]
- [[OpenAIClient]] - `uses` [INFERRED]
- [[context.py]] - `imports` [EXTRACTED]
- [[message.py]] - `imports` [EXTRACTED]
- [[models.py]] - `contains` [EXTRACTED]
- [[openai_client.py]] - `imports` [EXTRACTED]
- [[tool__init__.py]] - `imports` [EXTRACTED]

#graphify/code #graphify/EXTRACTED #community/ConversationContext