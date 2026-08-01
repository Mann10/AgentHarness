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


@pytest.mark.asyncio
async def test_system_skill_body_survives_summarization() -> None:
    """A system-role persist=False skill body survives _maybe_summarize() (ACT-04).

    The system-role exemption at context/context.py (m.role != "system") keeps
    loaded skill bodies out of the summarization payload — the body text must
    still be in to_llm_messages() after compaction fires.
    """
    call_count = 0

    async def mock_summarize(msgs: list[dict]) -> str:
        nonlocal call_count
        call_count += 1
        return "Summary."

    ctx = ConversationContext(
        count_tokens=lambda t: len(t.split()),
        token_limit=60,
        summarize_fn=mock_summarize,
        summarize_threshold=0.75,
        keep_recent_exchanges=0,
    )
    await ctx.add_message(Message(role="system", content="SKILL BODY", persist=False))
    for i in range(6):
        await ctx.add_user_message(f"Task {i} with some extra context here")
        await ctx.add_assistant_message(f"Response {i} with details and analysis")

    assert call_count >= 1, "Summarization should have fired above threshold"
    contents = [m["content"] for m in ctx.to_llm_messages()]
    assert "SKILL BODY" in contents


@pytest.mark.asyncio
async def test_skill_state_never_in_snapshot_meta_or_jsonl(store: JSONLSessionStore) -> None:
    """Session.skill_state is non-serialized by construction (ACT-05).

    The field must never appear in to_snapshot_meta() (explicit-copy omits it)
    nor in the saved JSONL session file.
    """
    session = Session.create("sys", count_tokens=len, token_limit=1000)
    assert session.skill_state == {}
    await session.context.add_user_message("help me")
    session.skill_state = {"demo-greeter": {"loaded": True}}
    assert "skill_state" not in session.to_snapshot_meta()
    await store.save(session)
    file_text = (store._dir / f"{session.id}.jsonl").read_text(encoding="utf-8")
    assert "skill_state" not in file_text


def test_skill_state_fresh_per_session() -> None:
    """skill_state is session-scoped — a fresh session starts with an empty dict (ACT-03)."""
    s1 = Session.create("sys", count_tokens=len, token_limit=1000)
    s2 = Session.create("sys", count_tokens=len, token_limit=1000)
    s1.skill_state = {"demo-greeter": {"loaded": True}}
    assert s2.skill_state == {}
