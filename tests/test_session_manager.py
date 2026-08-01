from __future__ import annotations

import tempfile

import pytest

from harness.session_manager import SessionManager
from session.store import JSONLSessionStore


@pytest.fixture
def mgr():
    """SessionManager with temp directory store."""
    tmpdir = tempfile.mkdtemp()
    store = JSONLSessionStore(tmpdir)
    return SessionManager(store)


@pytest.mark.asyncio
async def test_create_session_sets_active(mgr: SessionManager) -> None:
    session = await mgr.create_session(
        system_prompt="test",
        count_tokens=len,
        token_limit=1000,
    )
    assert mgr.active_session is not None
    assert mgr.active_session.id == session.id
    assert session.system_prompt == "test"


@pytest.mark.asyncio
async def test_create_session_persists(mgr: SessionManager) -> None:
    session = await mgr.create_session(
        system_prompt="test",
        count_tokens=len,
        token_limit=1000,
    )
    summaries = await mgr.list_sessions()
    ids = [s.id for s in summaries]
    assert session.id in ids


@pytest.mark.asyncio
async def test_load_session_sets_active(mgr: SessionManager) -> None:
    created = await mgr.create_session(
        system_prompt="test",
        count_tokens=len,
        token_limit=1000,
    )
    # Create a second session to show load switches active
    second = await mgr.create_session(
        system_prompt="second",
        count_tokens=len,
        token_limit=1000,
    )
    assert mgr.active_session.id == second.id

    loaded = await mgr.load_session(created.id)
    assert loaded is not None
    assert mgr.active_session.id == created.id


@pytest.mark.asyncio
async def test_load_nonexistent_returns_none(mgr: SessionManager) -> None:
    loaded = await mgr.load_session("nonexistent-id")
    assert loaded is None


@pytest.mark.asyncio
async def test_switch_session_saves_and_switches(mgr: SessionManager) -> None:
    first = await mgr.create_session(
        system_prompt="first",
        count_tokens=len,
        token_limit=1000,
    )
    second = await mgr.create_session(
        system_prompt="second",
        count_tokens=len,
        token_limit=1000,
    )
    assert mgr.active_session.id == second.id

    await mgr.switch_session(first)
    assert mgr.active_session.id == first.id


@pytest.mark.asyncio
async def test_save_session_idempotent_when_no_active(mgr: SessionManager) -> None:
    # No active session — save_session should not raise
    await mgr.save_session()


@pytest.mark.asyncio
async def test_delete_session_removes(mgr: SessionManager) -> None:
    session = await mgr.create_session(
        system_prompt="test",
        count_tokens=len,
        token_limit=1000,
    )
    await mgr.delete_session(session.id)
    summaries = await mgr.list_sessions()
    ids = [s.id for s in summaries]
    assert session.id not in ids


@pytest.mark.asyncio
async def test_delete_active_session_clears_active(mgr: SessionManager) -> None:
    session = await mgr.create_session(
        system_prompt="test",
        count_tokens=len,
        token_limit=1000,
    )
    assert mgr.active_session is not None
    await mgr.delete_session(session.id)
    assert mgr.active_session is None


@pytest.mark.asyncio
async def test_get_session_pure_read_does_not_switch_active(mgr: SessionManager) -> None:
    first = await mgr.create_session(system_prompt="first", count_tokens=len, token_limit=1000)
    second = await mgr.create_session(system_prompt="second", count_tokens=len, token_limit=1000)
    assert mgr.active_session.id == second.id
    loaded = await mgr.get_session(first.id)
    assert loaded is not None
    assert loaded.id == first.id
    assert mgr.active_session.id == second.id  # active unchanged — pure read


@pytest.mark.asyncio
async def test_get_session_nonexistent_returns_none(mgr: SessionManager) -> None:
    assert await mgr.get_session("nonexistent-id") is None
