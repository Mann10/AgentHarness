"""REPL /skill command tests (Phase 15 Plan 15-02).

Covers all four /skill branches in main._handle_session_cmd:
success / unknown / no-arg / already-loaded — plus a win32 case-variant
regression (D-04: name passed through raw; SkillStore.lookup handles
case-insensitivity) and a fall-through regression (/nonexistent → False).

The runtime is a MagicMock whose load_skill is an AsyncMock — the REPL is
in-process with RuntimeAPI (D-07) so the branch calls load_skill directly
and the mock stands in for the real runtime.
"""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock

import pytest

from main import _handle_session_cmd


@pytest.fixture
def runtime() -> MagicMock:
    """MagicMock runtime with an AsyncMock load_skill (D-07 direct-call seam)."""
    mock = MagicMock()
    mock.load_skill = AsyncMock()
    return mock


async def _run_cmd(
    line: str,
    runtime: MagicMock,
    capsys: pytest.CaptureFixture[str],
) -> tuple[bool, str]:
    """Call _handle_session_cmd and return (handled, captured stdout)."""
    handled = await _handle_session_cmd(line, {}, runtime, MagicMock(), MagicMock())
    return handled, capsys.readouterr().out


@pytest.mark.asyncio
async def test_skill_success_prints_ack_and_returns_true(
    runtime: MagicMock, capsys: pytest.CaptureFixture[str]
) -> None:
    """/skill <name> on a known skill prints the short ack and returns True (D-01, D-07)."""
    runtime.load_skill.return_value = "Loaded skill demo-greeter"

    handled, out = await _run_cmd("/skill demo-greeter", runtime, capsys)

    assert handled is True
    assert out.strip() == "Loaded skill demo-greeter"
    runtime.load_skill.assert_awaited_once_with("demo-greeter")


@pytest.mark.asyncio
async def test_skill_unknown_prints_not_found_and_returns_true(
    runtime: MagicMock, capsys: pytest.CaptureFixture[str]
) -> None:
    """/skill <unknown> prints the distinct error and returns True (D-02)."""
    runtime.load_skill.side_effect = KeyError("Unknown skill 'nosuch'")

    handled, out = await _run_cmd("/skill nosuch", runtime, capsys)

    assert handled is True
    assert out.strip() == "Skill 'nosuch' not found."
    runtime.load_skill.assert_awaited_once_with("nosuch")


@pytest.mark.asyncio
async def test_skill_no_arg_prints_usage_and_returns_true(
    runtime: MagicMock, capsys: pytest.CaptureFixture[str]
) -> None:
    """/skill with no argument prints a usage line and returns True — never a
    silent no-op or fall-through to chat (D-02)."""
    handled, out = await _run_cmd("/skill", runtime, capsys)

    assert handled is True
    assert "Usage: /skill" in out
    runtime.load_skill.assert_not_awaited()


@pytest.mark.asyncio
async def test_skill_already_loaded_prints_ack_and_returns_true(
    runtime: MagicMock, capsys: pytest.CaptureFixture[str]
) -> None:
    """/skill of an already-loaded skill prints the dedup ack and returns True —
    body never re-injected (D-03, exactly-once)."""
    runtime.load_skill.return_value = "Skill 'demo-greeter' already loaded"

    handled, out = await _run_cmd("/skill demo-greeter", runtime, capsys)

    assert handled is True
    assert out.strip() == "Skill 'demo-greeter' already loaded"


@pytest.mark.asyncio
async def test_skill_case_variant_passes_raw_name(
    runtime: MagicMock, capsys: pytest.CaptureFixture[str]
) -> None:
    """win32 case-variant (D-04): main.py does NOT normalize the name — the raw
    trimmed arg reaches load_skill and the (canonical) ack prints as-is."""
    runtime.load_skill.return_value = "Skill 'demo-greeter' already loaded"

    handled, out = await _run_cmd("/skill DEMO-GREETER", runtime, capsys)

    assert handled is True
    runtime.load_skill.assert_awaited_once_with("DEMO-GREETER")
    assert out.strip() == "Skill 'demo-greeter' already loaded"


@pytest.mark.asyncio
async def test_unknown_command_falls_through_to_false(
    runtime: MagicMock, capsys: pytest.CaptureFixture[str]
) -> None:
    """An unknown slash command still returns False — fall-through to chat is
    preserved for non-/skill commands."""
    handled, out = await _run_cmd("/nonexistent", runtime, capsys)

    assert handled is False
    assert out == ""
    runtime.load_skill.assert_not_awaited()
