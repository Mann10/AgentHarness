---
source_file: "tool/local_provider.py"
type: "code"
community: "LocalToolProvider"
location: "L87"
tags:
  - graphify/code
  - graphify/EXTRACTED
  - community/LocalToolProvider
---

# register_builtin_tools()

## Connections
- [[.add_tool()]] - `calls` [EXTRACTED]
- [[LocalToolProvider]] - `references` [EXTRACTED]
- [[_list_dir()]] - `indirect_call` [INFERRED]
- [[_read_file()]] - `indirect_call` [INFERRED]
- [[_write_file()]] - `indirect_call` [INFERRED]
- [[local_provider.py]] - `contains` [EXTRACTED]
- [[main()]] - `calls` [EXTRACTED]
- [[main.py]] - `imports` [EXTRACTED]
- [[tool__init__.py]] - `imports` [EXTRACTED]

#graphify/code #graphify/EXTRACTED #community/LocalToolProvider