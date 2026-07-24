# Community 1

> 19 nodes

## Key Concepts

- **ToolRegistry** (20 connections) — `tool/registry.py`
- **ToolProvider** (10 connections) — `tool/models.py`
- **.call_tool()** (5 connections) — `tool/registry.py`
- **._register_tools()** (4 connections) — `tool/registry.py`
- **.add_provider()** (3 connections) — `tool/registry.py`
- **.add_provider_tools()** (3 connections) — `tool/registry.py`
- **.list_tools()** (3 connections) — `tool/registry.py`
- **.call_tool()** (2 connections) — `tool/models.py`
- **.fetch_tools()** (2 connections) — `tool/models.py`
- **_summarize_args()** (2 connections) — `tool/registry.py`
- **._resolve_with_namespace()** (2 connections) — `tool/registry.py`
- **.start()** (2 connections) — `tool/registry.py`
- **Protocol** (1 connections)
- **.shutdown()** (1 connections) — `tool/models.py`
- **.start()** (1 connections) — `tool/models.py`
- **.__init__()** (1 connections) — `tool/registry.py`
- **.provider_count()** (1 connections) — `tool/registry.py`
- **.shutdown()** (1 connections) — `tool/registry.py`
- **.tool_count()** (1 connections) — `tool/registry.py`

## Relationships

- [Community 2](Community_2.md) (10 shared connections)
- [Community 4](Community_4.md) (8 shared connections)
- [Community 3](Community_3.md) (1 shared connections)

## Source Files

- `tool/models.py`
- `tool/registry.py`

## Audit Trail

- EXTRACTED: 60 (92%)
- INFERRED: 5 (8%)
- AMBIGUOUS: 0 (0%)

---

*Part of the graphify knowledge wiki. See [index](index.md) to navigate.*