from __future__ import annotations

from dataclasses import dataclass, field
from typing import Protocol, runtime_checkable


@runtime_checkable
class ToolProvider(Protocol):
    async def start(self) -> None: ...
    async def shutdown(self) -> None: ...
    async def fetch_tools(self) -> list[Tool]: ...
    async def call_tool(self, name: str, arguments: dict) -> ToolResult: ...


@dataclass
class Tool:
    name: str
    description: str
    input_schema: dict = field(default_factory=dict)


@dataclass
class ToolCall:
    id: str
    name: str
    arguments: dict


@dataclass
class ToolResult:
    tool_call_id: str
    content: str


@dataclass
class LLMResponse:
    content: str | None
    tool_calls: list[ToolCall] | None = None
