from __future__ import annotations

import asyncio
from collections.abc import Awaitable, Callable
from dataclasses import dataclass
from typing import Any

import pytest


@dataclass
class StubAgentResult:
    content: str = ""
    iterations: int = 0
    tool_calls_made: int = 0
    forced: bool = False


class StubAgent:
    """Minimal agent stub for scheduler and event tests.

    - delay: artificial pause before returning (simulate work)
    - fail: if True, raise RuntimeError on run()
    - hook: optional callback called before returning (for event assertions)
    """

    def __init__(
        self,
        delay: float = 0.0,
        fail: bool = False,
        emit: Callable[[Any], Awaitable[None]] | None = None,
    ) -> None:
        self.delay = delay
        self.fail = fail
        self._emit = emit or (lambda _: _dummy_awaitable())
        self.run_count = 0
        self.last_input: str = ""

    async def run(self, user_input: str) -> StubAgentResult:
        self.run_count += 1
        self.last_input = user_input
        if self.delay:
            await asyncio.sleep(self.delay)
        if self.fail:
            raise RuntimeError("StubAgent forced failure")
        return StubAgentResult(
            content=f"Echo: {user_input}",
            iterations=1,
            tool_calls_made=0,
        )

    async def start(self) -> None:
        pass

    async def shutdown(self) -> None:
        pass


@pytest.fixture
def stub_agent() -> StubAgent:
    return StubAgent()


@pytest.fixture
def slow_stub_agent() -> StubAgent:
    """Agent that takes 1 second per run -- for timeout/cancel tests."""
    return StubAgent(delay=1.0)


@pytest.fixture
def failing_stub_agent() -> StubAgent:
    """Agent that raises on run() -- for error event tests."""
    return StubAgent(fail=True)


async def _dummy_awaitable() -> None:
    pass
