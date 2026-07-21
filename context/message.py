from dataclasses import dataclass

VALID_ROLES = frozenset({"system", "user", "assistant"})


@dataclass
class Message:
    role: str
    content: str
    token_count: int = 0

    def __post_init__(self) -> None:
        if self.role not in VALID_ROLES:
            raise ValueError(f"Invalid role '{self.role}'. Must be one of {sorted(VALID_ROLES)}")
