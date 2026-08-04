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
    body_messages = [c for c in contents if "Hello body" in c]
    assert len(body_messages) == 1


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


# -- Test 7: loaded-skill token accounting (D-09/D-10/D-11/D-12) -------------


@pytest.mark.asyncio
async def test_load_skill_records_token_count(runtime: RuntimeAPI) -> None:
    """D-09: load_skill caches the per-skill token count in skill_state['loaded']."""
    await runtime.start()
    await runtime.load_skill("demo-greeter")

    loaded = runtime.active_session.skill_state["loaded"]
    rec = next(e for e in loaded if e["name"] == "demo-greeter")
    assert "tokens" in rec                      # D-09 record shape gains the token count
    assert isinstance(rec["tokens"], int)
    assert rec["tokens"] > 0


@pytest.mark.asyncio
async def test_load_skill_refuses_when_cap_exceeded_no_partial_state(
    runtime: RuntimeAPI, monkeypatch: pytest.MonkeyPatch
) -> None:
    """D-11: loading a skill that would exceed the cap refuses with a clear error
    naming the cap, leaves no partial state, and injects no body."""
    monkeypatch.setenv("LOADED_SKILL_TOKEN_CAP", "1")   # body > 1 token -> breach
    await runtime.start()

    with pytest.raises(RuntimeError, match="token cap.*would be exceeded"):
        await runtime.load_skill("demo-greeter")

    # no partial state (D-11): no record, no body message
    assert runtime.active_session.skill_state.get("loaded", []) == []
    contents = [m["content"] for m in runtime.active_session.context.to_llm_messages()]
    assert not any("Hello body" in c for c in contents)


@pytest.mark.asyncio
async def test_load_skill_cap_env_override_controls_refusal(
    runtime: RuntimeAPI, monkeypatch: pytest.MonkeyPatch
) -> None:
    """D-10/D-12: LOADED_SKILL_TOKEN_CAP is the env-var override - a generous cap
    lets the same skill through that a tiny cap refuses."""
    monkeypatch.setenv("LOADED_SKILL_TOKEN_CAP", "1000000")
    await runtime.start()

    ack = await runtime.load_skill("demo-greeter")
    assert "Loaded skill" in ack

    loaded = runtime.active_session.skill_state["loaded"]
    assert any(e["name"] == "demo-greeter" for e in loaded)


# -- Manifest attach: fresh session gets skill_manifest (Phase 12 seam) ------


@pytest.mark.asyncio
async def test_create_agent_attaches_manifest(runtime: RuntimeAPI) -> None:
    """A fresh session via RuntimeAPI has skill_manifest set when skills exist."""
    await runtime.start()
    manifest = runtime.active_session.skill_manifest
    assert manifest is not None
    assert "demo-greeter" in manifest


# -- H-01 regression: case-variant re-load (win32 D-07 exactly-once) ---------


@pytest.mark.asyncio
async def test_case_variant_reload_never_double_injects(runtime: RuntimeAPI) -> None:
    """H-01 regression (win32): loading 'demo-greeter' then 'DEMO-GREETER'
    must never double-inject — exactly one system body and one skill_state
    record. On win32 the second load is a no-op 'already loaded' ack; on
    posix the case-variant lookup raises KeyError. Either way the
    exactly-once contract (D-07, ACT-02) holds."""
    await runtime.start()
    await runtime.load_skill("demo-greeter")

    try:
        ack2 = await runtime.load_skill("DEMO-GREETER")
        assert "already loaded" in ack2.lower()
    except KeyError:
        pass  # posix: case-sensitive lookup — the variant is an unknown skill

    contents = [m["content"] for m in runtime.active_session.context.to_llm_messages()]
    assert len([c for c in contents if "Hello body" in c]) == 1

    loaded = runtime.active_session.skill_state["loaded"]
    assert len(loaded) == 1
    assert loaded[0]["name"] == "demo-greeter"
