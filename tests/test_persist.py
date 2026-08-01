from __future__ import annotations

import pytest

from context.context import ConversationContext
from context.message import Message


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
