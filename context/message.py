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

    def __post_init__(self) -> None:
        if self.role not in VALID_ROLES:
            raise ValueError(f"Invalid role '{self.role}'. Must be one of {sorted(VALID_ROLES)}")
