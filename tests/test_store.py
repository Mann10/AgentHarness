from __future__ import annotations

import tempfile
from datetime import datetime

import pytest

from session.models import Session
from session.store import JSONLSessionStore


@pytest.fixture
def store():
    return JSONLSessionStore(tempfile.mkdtemp())


@pytest.mark.asyncio
async def test_save_rewrites_meta_when_title_changes(store: JSONLSessionStore) -> None:
    """A title set after creation is persisted to the snapshot meta line."""
    session = Session.create("sys", count_tokens=len, token_limit=100)
    await store.save(session)
    session.title = "renamed title"
    await store.save(session)
    loaded = await store.load(session.id)
    assert loaded is not None
    assert loaded.title == "renamed title"


@pytest.mark.asyncio
async def test_save_persists_updated_at(store: JSONLSessionStore) -> None:
    """updated_at changes are written back to the snapshot meta line."""
    session = Session.create("sys", count_tokens=len, token_limit=100)
    await store.save(session)
    session.updated_at = datetime(2026, 1, 1, 12, 0, 0)
    await store.save(session)
    loaded = await store.load(session.id)
    assert loaded is not None
    assert loaded.updated_at.year == 2026


@pytest.mark.asyncio
async def test_save_appends_events_and_preserves_title(store: JSONLSessionStore) -> None:
    """Events accumulate across saves without losing the stored title."""
    session = Session.create("sys", count_tokens=len, token_limit=100)
    await store.save(session)
    session.title = "titled"
    await store.save(session)
    await session.context.add_user_message("hello")
    await session.context.add_assistant_message("hi back")
    await store.save(session)
    loaded = await store.load(session.id)
    assert loaded is not None
    assert loaded.title == "titled"
    assert len(loaded.get_messages()) == 2
