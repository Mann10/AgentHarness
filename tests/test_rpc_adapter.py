from __future__ import annotations

import pytest
from unittest.mock import AsyncMock, MagicMock

from backend.rpc.adapter import RPCAdapter
from backend.rpc.dispatcher import Dispatcher


def _adapter_with(history_result=None):
    runtime = MagicMock()
    runtime.get_session_history = AsyncMock(return_value=history_result)
    return RPCAdapter(runtime)


@pytest.mark.asyncio
async def test_sessions_get_missing_params_returns_error() -> None:
    adapter = _adapter_with()
    assert await adapter.handle_sessions_get(None) == {"error": "Missing 'session_id' in params"}


@pytest.mark.asyncio
async def test_sessions_get_rejects_path_traversal_session_id() -> None:
    """T-11-01: non-alnum session_id (path separators) never reaches the store."""
    adapter = _adapter_with()
    result = await adapter.handle_sessions_get({"session_id": "../../etc/passwd"})
    assert result == {"error": "Invalid session_id"}
    adapter._runtime.get_session_history.assert_not_called()


@pytest.mark.asyncio
async def test_sessions_get_returns_messages() -> None:
    adapter = _adapter_with(history_result=[{"role": "user", "content": "hi"}])
    result = await adapter.handle_sessions_get({"session_id": "a" * 32})
    assert result == {"messages": [{"role": "user", "content": "hi"}]}


@pytest.mark.asyncio
async def test_sessions_get_not_found_returns_error() -> None:
    adapter = _adapter_with(history_result=None)
    result = await adapter.handle_sessions_get({"session_id": "a" * 32})
    assert result == {"error": "Session not found"}


def test_sessions_get_registered_in_dispatcher() -> None:
    dispatcher = Dispatcher()
    _adapter_with().register_all(dispatcher)
    assert dispatcher._handlers["sessions.get"] is not None
