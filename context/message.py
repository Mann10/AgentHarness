from __future__ import annotations

from dataclasses import dataclass, field

from tool.models import ToolCall

VALID_ROLES = frozenset({"system", "user", "assistant", "tool"})


@dataclass
class Message:
    role: str
    content: str
    token_count: int = 0
    tool_calls: list[ToolCall] | None = None
    tool_call_id: str | None = None
    persist: bool = True

    def __post_init__(self) -> None:
        if self.role not in VALID_ROLES:
            raise ValueError(f"Invalid role '{self.role}'. Must be one of {sorted(VALID_ROLES)}")

    @classmethod
    def from_dict(cls, d: dict) -> Message:
        tool_calls = None
        if d.get("tool_calls"):
            tool_calls = [ToolCall(**tc) for tc in d["tool_calls"]]
        return cls(
            role=d["role"],
            content=d.get("content", ""),
            token_count=d.get("token_count", 0),
            tool_calls=tool_calls,
            tool_call_id=d.get("tool_call_id"),
            persist=d.get("persist", True),
        )
