from __future__ import annotations

import logging
from collections.abc import Awaitable, Callable
from typing import Any

from tool.models import Tool, ToolResult

logger = logging.getLogger(__name__)

RESERVED_SKILL_TOOLS = frozenset({"read_skill", "read_skill_path"})   # D-02


class SkillToolProvider:
    """Async __skills__ provider exposing the reserved read_skill/read_skill_path tools (D-01/D-02).

    Thin adapter: loading and path reads delegate to injected async handlers — the
    single shared RuntimeAPI.load_skill path (Pattern 3, D-09). Never touches
    Session/context directly.
    """
    def __init__(
        self,
        load_handler: Callable[[str], Awaitable[str]],
        read_handler: Callable[[str, str], Awaitable[str]],
    ) -> None:
        self._load_handler = load_handler     # (name) -> short ack (D-05)
        self._read_handler = read_handler     # (skill, rel_path) -> file content

    async def start(self) -> None:
        pass

    async def shutdown(self) -> None:
        pass

    async def fetch_tools(self) -> list[Tool]:
        return [
            Tool(
                name="read_skill",
                description="Load a skill's instructions into context. Use the skill name from the manifest — never a filesystem path. Returns a short confirmation; the instructions are added as a system message.",
                input_schema={"type": "object", "properties": {"name": {"type": "string"}}, "required": ["name"]},
            ),
            Tool(
                name="read_skill_path",
                description="Read a bundled resource (references/, scripts/, assets/) from an already-loaded skill. Path is relative to the skill's directory.",
                input_schema={"type": "object", "properties": {"skill": {"type": "string"}, "path": {"type": "string"}}, "required": ["skill", "path"]},
            ),
        ]

    async def call_tool(self, name: str, arguments: dict[str, Any]) -> ToolResult:
        if name == "read_skill":
            ack = await self._load_handler(arguments["name"])
            return ToolResult(tool_call_id=name, content=ack)
        if name == "read_skill_path":
            content = await self._read_handler(arguments["skill"], arguments["path"])
            return ToolResult(tool_call_id=name, content=content)
        raise ValueError(f"Unknown skill tool '{name}'")
