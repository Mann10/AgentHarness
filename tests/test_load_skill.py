from __future__ import annotations

import tempfile
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock

import pytest

from context.context import ConversationContext
from context.message import Message
from harness import RuntimeAPI
from session.store import JSONLSessionStore
from skills.store import SkillStore


@pytest.fixture
def skills_root(tmp_path: Path) -> Path:
    """A skills root with one demo skill (frontmatter-name authority, D-04)."""
    skill_dir = tmp_path / "demo-greeter"
    skill_dir.mkdir()
    (skill_dir / "SKILL.md").write_text(
        "---\nname: demo-greeter\ndescription: A demo skill\n---\n\n# Demo\n\nHello body\n",
        encoding="utf-8",
    )
    return tmp_path


@pytest.fixture
def store(skills_root: Path) -> SkillStore:
    return SkillStore(skills_root)


@pytest.fixture
def runtime(store: SkillStore) -> RuntimeAPI:
    """RuntimeAPI with stub LLM (test_runtime.py pattern) + real SkillStore."""
    config = MagicMock()
    config.system_prompt = "test"
    config.max_tokens = 1000
    config.max_tool_iterations = 5

    client = MagicMock()
    client.count_tokens = len

    async def _mock_chat_from_messages(messages, **kwargs):
        response = MagicMock()
        response.tool_calls = None
        response.content = "mock response"
        return response

    client.chat_from_messages = _mock_chat_from_messages

    registry = MagicMock()
    registry.list_tools = MagicMock(return_value=[])
    registry.start = AsyncMock()
    registry.shutdown = AsyncMock()

    return RuntimeAPI(
        config,
        client,
        registry,
        store=JSONLSessionStore(tempfile.mkdtemp()),
        skill_store=store,
        backlog_maxsize=5,
    )


# -- Test 1: Message.skill_name field (D-08 tag) -----------------------------


def test_message_skill_name_defaults_to_none() -> None:
    """skill_name defaults to None — normal messages are untagged."""
    msg = Message(role="user", content="hi")
    assert msg.skill_name is None


def test_message_from_dict_skill_name_defaults_to_none() -> None:
    """from_dict never reads a skill_name key (stored events never carry it)."""
    restored = Message.from_dict({"role": "user", "content": "x"})
    assert restored.skill_name is None


# -- Test 2: add_skill_message injection contract (D-06/D-08) ----------------


@pytest.mark.asyncio
async def test_add_skill_message_system_role_persist_false_tagged() -> None:
    """add_skill_message: system role, persist=False, skill_name tag, body visible."""
    ctx = ConversationContext(count_tokens=len, token_limit=1000)
    await ctx.add_skill_message("graphify", "BODY")

    msgs = ctx.to_llm_messages()
    assert msgs[-1]["role"] == "system"
    assert msgs[-1]["content"] == "BODY"

    tagged = ctx._messages[-1]
    assert tagged.persist is False
    assert tagged.skill_name == "graphify"


# -- Test 3: load_skill dedup (D-07) -----------------------------------------


@pytest.mark.asyncio
async def test_load_skill_dedup_no_op_second_load(runtime: RuntimeAPI) -> None:
    """Second load of the same skill is a no-op — body once, 'already loaded' ack."""
    await runtime.start()
    ack1 = await runtime.load_skill("demo-greeter")
    ack2 = await runtime.load_skill("demo-greeter")

    assert "already loaded" in ack2.lower()
    assert "Loaded skill" in ack1

    contents = [m["content"] for m in runtime.active_session.context.to_llm_messages()]
    assert contents.count("Hello body") == 1


# -- Test 4: skill_state["loaded"] records name + base dir (D-09) ------------


@pytest.mark.asyncio
async def test_load_skill_writes_skill_state(runtime: RuntimeAPI) -> None:
    """After load_skill, skill_state['loaded'] has the skill name and its base dir."""
    await runtime.start()
    await runtime.load_skill("demo-greeter")

    loaded = runtime.active_session.skill_state["loaded"]
    assert any(e["name"] == "demo-greeter" for e in loaded)
    assert any(e["dir"] for e in loaded)  # base dir recorded (D-09)


# -- Test 5: persist=False keeps the body out of JSONL (D-13) -----------------


@pytest.mark.asyncio
async def test_skill_body_never_serialized_to_jsonl(runtime: RuntimeAPI) -> None:
    """The loaded body never reaches the JSONL session file (D-13, ACT-05)."""
    await runtime.start()
    session = runtime.active_session
    await runtime.load_skill("demo-greeter")
    await runtime._session_manager.save_session()

    file_text = (
        runtime._session_manager._store._dir / f"{session.id}.jsonl"
    ).read_text(encoding="utf-8")
    assert "Hello body" not in file_text


# -- Test 6: unknown skill raises a clear error ------------------------------


@pytest.mark.asyncio
async def test_load_skill_unknown_raises_clear_error(runtime: RuntimeAPI) -> None:
    """An unknown skill name raises a clear error naming the skill."""
    await runtime.start()
    with pytest.raises(KeyError, match="no-such-skill"):
        await runtime.load_skill("no-such-skill")


# -- Manifest attach: fresh session gets skill_manifest (Phase 12 seam) ------


@pytest.mark.asyncio
async def test_create_agent_attaches_manifest(runtime: RuntimeAPI) -> None:
    """A fresh session via RuntimeAPI has skill_manifest set when skills exist."""
    await runtime.start()
    manifest = runtime.active_session.skill_manifest
    assert manifest is not None
    assert "demo-greeter" in manifest
