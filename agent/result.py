from dataclasses import dataclass


@dataclass
class AgentResult:
    content: str
    iterations: int = 0
    tool_calls_made: int = 0
    forced: bool = False