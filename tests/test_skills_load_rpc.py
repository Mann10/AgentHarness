from __future__ import annotations

import tempfile
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock

import pytest

from backend.rpc.adapter import RPCAdapter
from backend.rpc.dispatcher import Dispatcher
from backend.rpc.protocol import (
    RPCRequest,
    RPCError,
    INVALID_PARAMS,
    INTERNAL_ERROR,
    SKILL_NOT_FOUND,
    RPC_METHODS,
)
from harness import RuntimeAPI
from session.store import JSONLSessionStore
from skills.store import SkillStore


def _adapter_with(load_status_result=None, load_status_side_effect=None):
    """Adapter with a MagicMock runtime exposing load_skill_status (D-06)."""
    runtime = MagicMock()
    runtime.load_skill_status = AsyncMock(
        return_value=load_status_result,
        side_effect=load_status_side_effect,
    )
    return RPCAdapter(runtime)


# -- Test 1: whitelist (D-05) ------------------------------------------------


def test_rpc_methods_whitelist_has_skills_load() -> None:
    """'skills.load' is whitelisted in RPC_METHODS (D-05, sessions.* pattern)."""
    assert "skills.load" in RPC_METHODS


# -- Test 2: domain error code (D-08) ----------------------------------------


def test_skill_not_found_code_is_minus_32001() -> None:
    """SKILL_NOT_FOUND is the D-08 domain code -32001."""
    assert SKILL_NOT_FOUND == -32001


# -- Test 3: RPCError passthrough (dispatcher) --------------------------------


@pytest.mark.asyncio
async def test_dispatcher_passes_through_rpc_error_code() -> None:
    """A handler raising RPCError returns that code/message — not -32603."""
    dispatcher = Dispatcher()

    async def _handler(params):
        raise RPCError(code=SKILL_NOT_FOUND, message="Skill 'x' not found.")

    dispatcher.register("skills.load", _handler)
    resp = await dispatcher.dispatch(
        RPCRequest(id=1, method="skills.load", params={})
    )
    assert resp.error is not None
    assert resp.error.code == SKILL_NOT_FOUND
    assert resp.error.message == "Skill 'x' not found."


# -- Test 4: -32603 regression (dispatcher) -----------------------------------


@pytest.mark.asyncio
async def test_dispatcher_wraps_unknown_exception_as_internal_error() -> None:
    """Unknown exceptions still wrap as INTERNAL_ERROR (-32603)."""
    dispatcher = Dispatcher()

    def _handler(params):
        raise ValueError("boom")

    dispatcher.register("chat", _handler)
    resp = await dispatcher.dispatch(RPCRequest(id=1, method="chat", params={}))
    assert resp.error is not None
    assert resp.error.code == INTERNAL_ERROR


# -- Test 5: INVALID_PARAMS (D-08, missing/invalid name) ----------------------


@pytest.mark.asyncio
async def test_handle_skills_load_missing_name_raises_invalid_params() -> None:
    """None/empty/non-str name raises RPCError INVALID_PARAMS (-32602)."""
    adapter = _adapter_with()
    for bad in (None, {}, {"name": ""}, {"name": "   "}, {"name": 123}):
        with pytest.raises(RPCError) as exc:
            await adapter.handle_skills_load(bad)
        assert exc.value.code == INVALID_PARAMS


# -- Test 6: SKILL_NOT_FOUND mapping (D-08, unknown skill) ---------------------


@pytest.mark.asyncio
async def test_handle_skills_load_unknown_skill_raises_skill_not_found() -> None:
    """KeyError from runtime maps to RPCError SKILL_NOT_FOUND naming the skill."""
    runtime = MagicMock()
    runtime.load_skill_status = AsyncMock(
        side_effect=KeyError("no-such-skill")
    )
    adapter = RPCAdapter(runtime)

    with pytest.raises(RPCError) as exc:
        await adapter.handle_skills_load({"name": "no-such-skill"})
    assert exc.value.code == SKILL_NOT_FOUND
    assert "no-such-skill" in exc.value.message


# -- Test 7: loaded status (D-06) ----------------------------------------------


@pytest.mark.asyncio
async def test_handle_skills_load_returns_loaded_status() -> None:
    """The handler returns the runtime's {skill, status} result verbatim."""
    adapter = _adapter_with(
        load_status_result={"skill": "demo-greeter", "status": "loaded"}
    )
    result = await adapter.handle_skills_load({"name": "demo-greeter"})
    assert result == {"skill": "demo-greeter", "status": "loaded"}


# -- Test 8: register_all registration (T-15-01) -------------------------------


def test_skills_load_registered_in_dispatcher() -> None:
    """register_all registers 'skills.load' → handle_skills_load."""
    dispatcher = Dispatcher()
    _adapter_with().register_all(dispatcher)
    assert dispatcher._handlers["skills.load"] is not None


# -- Test 9: already_loaded dedup (H-01) via real RuntimeAPI -------------------


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


@pytest.mark.asyncio
async def test_load_skill_status_dedup_already_loaded(runtime: RuntimeAPI) -> None:
    """load_skill_status: first load → 'loaded', second → 'already_loaded' (H-01)."""
    await runtime.start()
    first = await runtime.load_skill_status("demo-greeter")
    assert first == {"skill": "demo-greeter", "status": "loaded"}

    second = await runtime.load_skill_status("demo-greeter")
    assert second == {"skill": "demo-greeter", "status": "already_loaded"}

    # body injected exactly once (D-07 exactly-once)
    contents = [m["content"] for m in runtime.active_session.context.to_llm_messages()]
    assert len([c for c in contents if "Hello body" in c]) == 1
