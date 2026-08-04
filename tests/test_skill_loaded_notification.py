from __future__ import annotations

import tempfile
from pathlib import Path
from unittest.mock import MagicMock

import pytest

from backend.rpc.protocol import RPCRequest
from backend.rpc.server import RPCServer
from harness import RuntimeAPI
from harness.events import EVENT_SKILL_LOADED, SkillLoadedEvent
from session.store import JSONLSessionStore
from skills.store import SkillStore
from tool.registry import ToolRegistry


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


def _make_stub_client(*, max_tokens: int = 1000) -> tuple[MagicMock, MagicMock]:
    """Config + stub OpenAIClient (test_load_skill pattern)."""
    config = MagicMock()
    config.system_prompt = "test"
    config.max_tokens = max_tokens
    config.max_tool_iterations = 5

    client = MagicMock()
    client.count_tokens = len

    async def _chat_from_messages(messages, **kwargs):
        response = MagicMock()
        response.tool_calls = None
        response.content = "mock response"
        return response

    client.chat_from_messages = _chat_from_messages
    return config, client


def _build_runtime(
    skills_root: Path,
    *,
    max_tokens: int = 1000,
    store_dir: str | None = None,
) -> RuntimeAPI:
    """The REAL stack (D-15): SkillStore + real ToolRegistry + SkillToolProvider
    bound to the runtime's load/read handlers. Only the LLM client is stubbed."""
    config, client = _make_stub_client(max_tokens=max_tokens)

    registry = ToolRegistry()
    skill_store = SkillStore(skills_root)
    runtime = RuntimeAPI(
        config,
        client,
        registry,
        store=JSONLSessionStore(store_dir or tempfile.mkdtemp()),
        skill_store=skill_store,
    )
    # Register the __skills__ provider before start (main.py wiring pattern, D-03).
    registry.add_provider("__skills__", runtime.make_skill_provider(), namespace=None)
    return runtime


async def _attach_collector(runtime: RuntimeAPI) -> list:
    """Subscribe a collector for SkillLoadedEvent on the runtime's bus."""
    received: list = []

    async def collector(event) -> None:
        received.append(event)

    await runtime.event_bus.subscribe(EVENT_SKILL_LOADED, collector)
    return received


# -- Dimension 1: emission on BOTH activation paths (D-07) -------------------


@pytest.mark.asyncio
async def test_load_skill_emits_skill_loaded_event(skills_root: Path) -> None:
    """User-driven load (runtime.load_skill) emits exactly one SkillLoadedEvent
    carrying the canonical name + session_id (D-07 shared path)."""
    runtime = _build_runtime(skills_root)
    await runtime.start()
    received = await _attach_collector(runtime)

    await runtime.load_skill("demo-greeter")

    assert len(received) == 1
    assert isinstance(received[0], SkillLoadedEvent)
    assert received[0].skill == "demo-greeter"
    assert received[0].session_id == runtime.active_session.id


@pytest.mark.asyncio
async def test_model_driven_read_skill_emits_event(skills_root: Path) -> None:
    """Model-driven load (read_skill via the __skills__ provider) emits exactly
    one SkillLoadedEvent — both activation paths share load_skill (D-07)."""
    runtime = _build_runtime(skills_root)
    await runtime.start()
    received = await _attach_collector(runtime)

    provider = runtime.make_skill_provider()
    await provider.call_tool("read_skill", {"name": "demo-greeter"})

    assert len(received) == 1
    assert isinstance(received[0], SkillLoadedEvent)
    assert received[0].skill == "demo-greeter"


# -- Dimension 2: zero events on no-op paths (D-07) ---------------------------


@pytest.mark.asyncio
async def test_already_loaded_emits_no_event(skills_root: Path) -> None:
    """already_loaded returns early in load_skill and emits no notification."""
    runtime = _build_runtime(skills_root)
    await runtime.start()
    await runtime.load_skill("demo-greeter")

    received = await _attach_collector(runtime)
    ack2 = await runtime.load_skill("demo-greeter")

    assert "already loaded" in ack2.lower()
    assert len(received) == 0


@pytest.mark.asyncio
async def test_not_found_emits_no_event(skills_root: Path) -> None:
    """Unknown skill raises KeyError and emits no notification."""
    runtime = _build_runtime(skills_root)
    await runtime.start()
    received = await _attach_collector(runtime)

    with pytest.raises(KeyError):
        await runtime.load_skill("nope")

    assert len(received) == 0


@pytest.mark.asyncio
async def test_cap_refusal_emits_no_event(skills_root: Path, monkeypatch) -> None:
    """Cap refusal raises RuntimeError and emits no notification (load didn't
    happen — the chip must never show a skill whose body is not in context)."""
    monkeypatch.setenv("LOADED_SKILL_TOKEN_CAP", "1")
    runtime = _build_runtime(skills_root)
    await runtime.start()
    received = await _attach_collector(runtime)

    with pytest.raises(RuntimeError, match="token cap.*would be exceeded"):
        await runtime.load_skill("demo-greeter")

    assert len(received) == 0


# -- Dimension 3: exact wire format (D-06, {skill} only) ----------------------


@pytest.mark.asyncio
async def test_event_maps_to_notification_wire_format() -> None:
    """SkillLoadedEvent maps to the exact JSON-RPC notification dict the TUI
    parses: type=skill_loaded, request_id=session_id, payload={skill} only."""
    server = RPCServer(MagicMock())
    notif = server._event_to_notification(
        SkillLoadedEvent(session_id="sess-1", skill="demo-greeter")
    )
    assert notif == {
        "jsonrpc": "2.0",
        "method": "event",
        "params": {
            "type": "skill_loaded",
            "request_id": "sess-1",
            "payload": {"skill": "demo-greeter"},
        },
    }


@pytest.mark.asyncio
async def test_payload_is_skill_only() -> None:
    """D-06: the notification payload has exactly the 'skill' key — no status,
    no session_id, no event_id leak."""
    server = RPCServer(MagicMock())
    notif = server._event_to_notification(
        SkillLoadedEvent(session_id="sess-1", skill="demo-greeter")
    )
    assert set(notif["params"]["payload"].keys()) == {"skill"}
    assert notif["params"]["payload"] == {"skill": "demo-greeter"}


# -- Dimension 4: RPC round trip (independent channels, Pitfall 2) ------------


@pytest.mark.asyncio
async def test_skills_load_rpc_round_trip_emits_notification(
    skills_root: Path, monkeypatch
) -> None:
    """skills.load RPC round trip through the real stack: the response carries
    {skill, status} AND exactly one skill_loaded notification is written.
    Assert the two channels INDEPENDENTLY — the notification fires inside the
    await in load_skill, BEFORE the dispatcher writes the response."""
    runtime = _build_runtime(skills_root)
    await runtime.start()

    server = RPCServer(runtime)
    writes: list = []
    monkeypatch.setattr("backend.rpc.server._write_json", writes.append)
    # Manual subscribe reproduces exactly what server.start() does (no stdin
    # read loop under pytest).
    await runtime.event_bus.subscribe(EVENT_SKILL_LOADED, server._on_event)

    resp = await server._dispatcher.dispatch(
        RPCRequest(id=1, method="skills.load", params={"name": "demo-greeter"})
    )

    # Channel (a): the RPC response.
    assert resp.error is None
    assert resp.result == {"skill": "demo-greeter", "status": "loaded"}

    # Channel (b): the notification — written as a JSON-RPC event.
    events = [w for w in writes if w.get("method") == "event"]
    assert len(events) == 1
    assert events[0]["params"]["type"] == "skill_loaded"
    assert events[0]["params"]["payload"] == {"skill": "demo-greeter"}


# -- Dimension 5: no conversation pollution (ROADMAP criterion 4) -------------


@pytest.mark.asyncio
async def test_load_skill_adds_no_conversation_message(skills_root: Path) -> None:
    """load_skill adds exactly the system-role body to llm messages — no
    user/assistant message carries the body (no stream pollution)."""
    runtime = _build_runtime(skills_root)
    await runtime.start()
    await runtime.load_skill("demo-greeter")

    msgs = runtime.active_session.to_llm_messages()
    bodies = [m for m in msgs if "Hello body" in m["content"]]
    assert len(bodies) == 1
    assert bodies[0]["role"] == "system"
    polluted = [
        m for m in msgs if m["role"] in ("user", "assistant") and "Hello body" in m["content"]
    ]
    assert len(polluted) == 0
