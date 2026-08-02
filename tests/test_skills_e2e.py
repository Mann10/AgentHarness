from __future__ import annotations

import tempfile
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock

import pytest

from harness import RuntimeAPI
from session.store import JSONLSessionStore
from skills.store import SkillStore
from tool.registry import ToolRegistry


@pytest.fixture
def skills_root(tmp_path: Path) -> Path:
    """Skills root with demo-greeter: SKILL.md + bundled references/guide.md (CAP-01)."""
    skill_dir = tmp_path / "demo-greeter"
    skill_dir.mkdir()
    (skill_dir / "SKILL.md").write_text(
        "---\nname: demo-greeter\ndescription: A demo skill\n---\n\n# Demo\n\nHello body\n",
        encoding="utf-8",
    )
    (skill_dir / "references").mkdir()
    (skill_dir / "references" / "guide.md").write_text(
        "GUIDE REFERENCE CONTENT\n", encoding="utf-8"
    )
    return tmp_path


def _make_stub_client(*, max_tokens: int = 1000) -> tuple[MagicMock, MagicMock, list]:
    """Config + stub OpenAIClient (test_load_skill pattern); returns (config, client, chat_log)."""
    config = MagicMock()
    config.system_prompt = "test"
    config.max_tokens = max_tokens
    config.max_tool_iterations = 5

    client = MagicMock()
    client.count_tokens = len

    chat_log: list[list[dict]] = []

    async def _chat_from_messages(messages, **kwargs):
        chat_log.append(messages)
        response = MagicMock()
        response.tool_calls = None
        response.content = "mock response"
        return response

    client.chat_from_messages = _chat_from_messages
    return config, client, chat_log


def _build_runtime(
    skills_root: Path,
    *,
    max_tokens: int = 1000,
    store_dir: str | None = None,
) -> RuntimeAPI:
    """The REAL stack (D-15): SkillStore + real ToolRegistry + SkillToolProvider
    bound to the runtime's load/read handlers. Only the LLM client is stubbed."""
    config, client, _ = _make_stub_client(max_tokens=max_tokens)

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


# -- Test 1: load -> inject (D-05/D-06) --------------------------------------


@pytest.mark.asyncio
async def test_e2e_load_skill_injects_body_exactly_once(skills_root: Path) -> None:
    """load_skill returns the short ack; the body appears exactly once as a
    system message in to_llm_messages (D-05 — no duplication)."""
    runtime = _build_runtime(skills_root)
    await runtime.start()

    ack = await runtime.load_skill("demo-greeter")
    assert ack == "Loaded skill demo-greeter"

    msgs = runtime.active_session.to_llm_messages()
    bodies = [m for m in msgs if "Hello body" in m["content"]]
    assert len(bodies) == 1
    assert bodies[0]["role"] == "system"


# -- Test 2: dedup exactly-once (D-07, ACT-02) -------------------------------


@pytest.mark.asyncio
async def test_second_load_is_noop_body_still_once(skills_root: Path) -> None:
    """Re-loading an already-loaded skill returns an 'already loaded' ack and
    the body still appears exactly once (D-07 no-op, ACT-02 exactly-once)."""
    runtime = _build_runtime(skills_root)
    await runtime.start()

    await runtime.load_skill("demo-greeter")
    ack2 = await runtime.load_skill("demo-greeter")
    assert "already loaded" in ack2.lower()

    msgs = runtime.active_session.to_llm_messages()
    bodies = [m for m in msgs if "Hello body" in m["content"]]
    assert len(bodies) == 1


# -- Test 3: summarize-survive (Phase 13 system exemption, D-15) -------------


@pytest.mark.asyncio
async def test_skill_body_survives_summarization(skills_root: Path) -> None:
    """Forced summarization (tiny token_limit) must not remove the system-role
    skill body from to_llm_messages (Phase 13 exemption, ACT-04)."""
    config, client, chat_log = _make_stub_client(max_tokens=60)

    registry = MagicMock()
    registry.list_tools = MagicMock(return_value=[])
    registry.start = AsyncMock()
    registry.shutdown = AsyncMock()

    runtime = RuntimeAPI(
        config,
        client,
        registry,
        store=JSONLSessionStore(tempfile.mkdtemp()),
        skill_store=SkillStore(skills_root),
    )
    await runtime.start()
    await runtime.load_skill("demo-greeter")

    session = runtime.active_session
    # Push accumulated traffic past token_limit * 0.75 (60 * 0.75 = 45 chars).
    for i in range(8):
        await session.context.add_user_message(f"Task {i} with some extra context here")
        await session.context.add_assistant_message(f"Response {i} with details and analysis")

    # chat_from_messages is only invoked through the runtime's summarize_fn —
    # at least one call proves summarization fired.
    assert chat_log, "summarization should have fired above the threshold"

    contents = [m["content"] for m in session.to_llm_messages()]
    assert any("Hello body" in c for c in contents), (
        "system-role skill body must survive summarization (Phase 13 exemption)"
    )


# -- Test 4: JSONL untouched (D-13, D-15) -------------------------------------


@pytest.mark.asyncio
async def test_skill_body_never_reaches_jsonl(skills_root: Path) -> None:
    """persist=False body is absent from the saved session file while
    user/assistant traffic is present (D-13 leak closed, D-15)."""
    store_dir = tempfile.mkdtemp()
    runtime = _build_runtime(skills_root, store_dir=store_dir)
    await runtime.start()

    session = runtime.active_session
    await runtime.load_skill("demo-greeter")
    await session.context.add_user_message("hello there")
    await session.context.add_assistant_message("hi back")
    await runtime._session_manager.save_session()

    file_text = (Path(store_dir) / f"{session.id}.jsonl").read_text(encoding="utf-8")
    assert "Hello body" not in file_text
    assert "hello there" in file_text
    assert "hi back" in file_text


# -- Test 5: read_skill_path through the real provider (CAP-01) ---------------


@pytest.mark.asyncio
async def test_read_skill_path_returns_bundled_reference(skills_root: Path) -> None:
    """CAP-01: read_skill_path via the real SkillToolProvider + SkillStore
    returns the bundled reference file content."""
    runtime = _build_runtime(skills_root)
    await runtime.start()

    provider = runtime.make_skill_provider()
    result = await provider.call_tool(
        "read_skill_path", {"skill": "demo-greeter", "path": "references/guide.md"}
    )
    assert "GUIDE REFERENCE CONTENT" in result.content
