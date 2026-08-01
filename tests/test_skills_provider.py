"""Provider-surface + retention-contract tests for the __skills__ tool provider (Plan 14-02).

Covers:
  - D-01/D-02: fetch_tools returns exactly the two reserved, un-namespaced
    tool names read_skill + read_skill_path
  - D-05: call_tool("read_skill") dispatches to the injected load_handler and
    returns its short ack as the ToolResult — the body is NOT in the result
  - Handler dispatch: read_skill_path routes (skill, path) to read_handler
  - Unknown tool names raise ValueError
  - CAP-03: retain_read_skills keeps read_skill/read_skill_path in every
    allowed-tools filter (allowed ∪ reserved); allowed=None passes all
  - D-03: the registry reserved-name guard rejects a provider colliding with
    read_skill — a skill can never shadow or be shadowed
"""

from __future__ import annotations

import pytest

from skills.filter import RESERVED_SKILL_TOOLS as FILTER_RESERVED
from skills.filter import retain_read_skills
from skills.provider import RESERVED_SKILL_TOOLS as PROVIDER_RESERVED
from skills.provider import SkillToolProvider
from tool.models import Tool, ToolResult
from tool.registry import ToolRegistry


async def _ack(name: str) -> str:
    return f"Loaded skill {name}"


async def _body(skill: str, rel: str) -> str:
    return f"body of {skill}/{rel}"


@pytest.fixture
def provider() -> SkillToolProvider:
    return SkillToolProvider(load_handler=_ack, read_handler=_body)


# --- D-01/D-02: fetch_tools surface ------------------------------------------


async def test_fetch_tools_returns_exactly_two_reserved_tools(provider: SkillToolProvider) -> None:
    tools = await provider.fetch_tools()
    assert [t.name for t in tools] == ["read_skill", "read_skill_path"]


async def test_fetch_tools_tools_are_un_namespaced(provider: SkillToolProvider) -> None:
    """The LLM sees exactly read_skill/read_skill_path — no `__skills__` prefix (D-02)."""
    tools = await provider.fetch_tools()
    assert all(not t.name.startswith("__skills__") for t in tools)


async def test_fetch_tools_schemas_require_name(provider: SkillToolProvider) -> None:
    read_skill, read_skill_path = await provider.fetch_tools()
    assert read_skill.input_schema.get("required") == ["name"]
    assert read_skill_path.input_schema.get("required") == ["skill", "path"]
    assert read_skill.description and read_skill_path.description  # LLM-facing docs


# --- D-05: read_skill dispatch + short-ack result ----------------------------


async def test_call_tool_read_skill_dispatch_and_ack() -> None:
    """call_tool("read_skill", {"name": "x"}) calls load_handler("x") and returns
    the short ack as ToolResult — the body is NOT duplicated in the result (D-05)."""
    body = "SECRET-SKILL-BODY"
    calls: list[str] = []

    async def handler(name: str) -> str:
        calls.append(name)
        return f"Loaded skill {name}"  # ack only — body flows via system message

    provider = SkillToolProvider(load_handler=handler, read_handler=_body)
    result = await provider.call_tool("read_skill", {"name": "x"})
    assert calls == ["x"]
    assert isinstance(result, ToolResult)
    assert result.tool_call_id == "read_skill"
    assert result.content == "Loaded skill x"
    assert body not in result.content  # D-05: never duplicated in the tool result


# --- read_skill_path dispatch ------------------------------------------------


async def test_call_tool_read_skill_path_dispatch() -> None:
    """call_tool routes (skill, path) to the injected read_handler and returns
    the file content."""
    calls: list[tuple[str, str]] = []

    async def handler(skill: str, rel: str) -> str:
        calls.append((skill, rel))
        return "guide body"

    provider = SkillToolProvider(load_handler=_ack, read_handler=handler)
    result = await provider.call_tool(
        "read_skill_path", {"skill": "x", "path": "references/guide.md"}
    )
    assert calls == [("x", "references/guide.md")]
    assert isinstance(result, ToolResult)
    assert result.tool_call_id == "read_skill_path"
    assert result.content == "guide body"


# --- unknown tool name --------------------------------------------------------


async def test_call_tool_unknown_name_raises(provider: SkillToolProvider) -> None:
    with pytest.raises(ValueError) as exc:
        await provider.call_tool("bogus", {})
    assert "bogus" in str(exc.value)


# --- CAP-03: retention contract ----------------------------------------------

BASE_TOOLS = [
    Tool(name="read_skill", description="", input_schema={}),
    Tool(name="read_skill_path", description="", input_schema={}),
    Tool(name="read_file", description="", input_schema={}),
    Tool(name="write_file", description="", input_schema={}),
]


def test_retain_empty_allowed_keeps_only_reserved() -> None:
    """allowed=[] → only the two skill tools survive (CAP-03 deadlock guard)."""
    kept = retain_read_skills(BASE_TOOLS, set())
    assert [t.name for t in kept] == ["read_skill", "read_skill_path"]


def test_retain_union_with_allowed_keeps_reserved() -> None:
    """allowed=["read_file"] → read_file PLUS the two skill tools."""
    kept = retain_read_skills(BASE_TOOLS, {"read_file"})
    names = [t.name for t in kept]
    assert "read_file" in names
    assert "read_skill" in names
    assert "read_skill_path" in names
    assert "write_file" not in names


def test_retain_none_returns_all_unchanged() -> None:
    """allowed=None → no restriction; every tool passes through unchanged."""
    kept = retain_read_skills(BASE_TOOLS, None)
    assert kept == BASE_TOOLS
    assert len(kept) == 4


def test_reserved_constant_matches_contract() -> None:
    """The reserved set is shared by provider and filter — one source of truth."""
    assert PROVIDER_RESERVED == frozenset({"read_skill", "read_skill_path"})
    assert FILTER_RESERVED == frozenset({"read_skill", "read_skill_path"})


# --- D-03: reserved-name collision guard -------------------------------------


class _StubToolProvider:
    """Minimal ToolProvider-shaped stub that holds the reserved read_skill name."""

    async def start(self) -> None: ...

    async def shutdown(self) -> None: ...

    async def fetch_tools(self) -> list[Tool]:
        return [
            Tool(name="read_skill", description="stub holding reserved name"),
            Tool(name="other_tool", description="stub"),
        ]

    async def call_tool(self, name: str, arguments: dict) -> ToolResult:
        return ToolResult(tool_call_id=name, content="stub")


async def test_registry_reserved_name_collision_raises() -> None:
    """D-03: a provider already holding read_skill + the __skills__ provider
    → _register_tools raises ValueError naming the reserved tool. A skill can
    never shadow or be shadowed."""
    registry = ToolRegistry()
    stub = _StubToolProvider()
    registry.add_provider("stub", stub)
    registry._register_tools("stub", await stub.fetch_tools())  # private, mirrors test_persist.py

    provider = SkillToolProvider(load_handler=_ack, read_handler=_body)
    with pytest.raises(ValueError) as exc:
        registry._register_tools("__skills__", await provider.fetch_tools())
    message = str(exc.value)
    assert "read_skill" in message
    assert "stub" in message
