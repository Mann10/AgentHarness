from __future__ import annotations

import tempfile

import pytest

from context.context import ConversationContext
from context.message import Message
from session.models import Session
from session.store import JSONLSessionStore


@pytest.fixture
def store() -> JSONLSessionStore:
    return JSONLSessionStore(tempfile.mkdtemp())


def test_default_persist_is_true() -> None:
    """Messages persist by default — backward compatible with existing callers."""
    msg = Message(role="user", content="hi")
    assert msg.persist is True


def test_explicit_persist_false() -> None:
    """Skill-body messages can opt out of persistence explicitly."""
    msg = Message(role="system", content="body", persist=False)
    assert msg.persist is False


def test_from_dict_defaults_to_persist() -> None:
    """Stored events (which never carry the persist key) default to persist=True."""
    msg = Message.from_dict({"role": "user", "content": "x", "token_count": 1})
    assert msg.persist is True


@pytest.mark.asyncio
async def test_persist_false_message_visible_in_to_llm_messages() -> None:
    """A persist=False system message still appears in to_llm_messages every turn (ACT-03)."""
    ctx = ConversationContext(count_tokens=len, token_limit=1000)
    await ctx.add_message(Message(role="system", content="SKILL BODY", persist=False))
    assert "SKILL BODY" in [m["content"] for m in ctx.to_llm_messages()]


@pytest.mark.asyncio
async def test_persist_false_message_never_written_to_jsonl(store: JSONLSessionStore) -> None:
    """A persist=False message never reaches the JSONL session file (D-13 leak closed, ACT-05)."""
    session = Session.create("sys", count_tokens=len, token_limit=1000)
    await session.context.add_user_message("help me")
    await session.context.add_message(Message(role="system", content="SKILL-BODY-SECRET", persist=False))
    await session.context.add_assistant_message("sure thing")
    await store.save(session)
    file_text = (store._dir / f"{session.id}.jsonl").read_text(encoding="utf-8")
    assert "SKILL-BODY-SECRET" not in file_text
    assert "help me" in file_text
    assert "sure thing" in file_text


@pytest.mark.asyncio
async def test_resumed_session_has_no_skill_body(store: JSONLSessionStore) -> None:
    """A resumed session (save -> load -> restore_context) has exactly the persisted messages."""
    session = Session.create("sys", count_tokens=len, token_limit=1000)
    await session.context.add_user_message("help me")
    await session.context.add_message(Message(role="system", content="SKILL-BODY-SECRET", persist=False))
    await session.context.add_assistant_message("sure thing")
    await store.save(session)
    loaded = await store.load(session.id)
    assert loaded is not None
    await loaded.restore_context(count_tokens=len, token_limit=1000)
    contents = [ev["content"] for ev in loaded.to_events()]
    assert "SKILL-BODY-SECRET" not in contents
    assert "help me" in contents
    assert "sure thing" in contents


@pytest.mark.asyncio
async def test_repeated_saves_with_persist_false_no_duplicate_events(
    store: JSONLSessionStore,
) -> None:
    """Consecutive saves with a persist=False message present append each event exactly once."""
    session = Session.create("sys", count_tokens=len, token_limit=1000)
    await session.context.add_user_message("help me")
    await session.context.add_message(Message(role="system", content="SKILL-BODY-SECRET", persist=False))
    await session.context.add_assistant_message("sure thing")
    await store.save(session)
    await session.context.add_user_message("next question")
    await store.save(session)
    file_text = (store._dir / f"{session.id}.jsonl").read_text(encoding="utf-8")
    assert file_text.count("sure thing") == 1
    assert file_text.count("next question") == 1
    assert "SKILL-BODY-SECRET" not in file_text


@pytest.mark.asyncio
async def test_persist_false_between_saves_does_not_shift_index(
    store: JSONLSessionStore,
) -> None:
    """A persist=False message added between saves must not shift the write index."""
    session = Session.create("sys", count_tokens=len, token_limit=1000)
    await session.context.add_user_message("help me")
    await session.context.add_assistant_message("sure thing")
    await store.save(session)
    await session.context.add_message(Message(role="system", content="SKILL-BODY-SECRET", persist=False))
    await session.context.add_user_message("next question")
    await store.save(session)
    file_text = (store._dir / f"{session.id}.jsonl").read_text(encoding="utf-8")
    assert file_text.count("sure thing") == 1
    assert file_text.count("next question") == 1
    assert "SKILL-BODY-SECRET" not in file_text
