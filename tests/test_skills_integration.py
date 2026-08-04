from __future__ import annotations

from pathlib import Path

from session.models import Session
from skills import build_manifest_text, discover_skills


def _write_skill(root: Path, folder: str, name: str, description: str) -> None:
    d = root / folder
    d.mkdir(parents=True, exist_ok=True)
    (d / "SKILL.md").write_text(
        f"---\nname: {name}\ndescription: {description}\n---\n\n# body\n",
        encoding="utf-8",
    )


def _session_with_manifest(root: Path) -> Session:
    session = Session.create("base prompt", count_tokens=len, token_limit=1000)
    session.skill_manifest = build_manifest_text(discover_skills(root), max_chars=1500)
    return session


def test_manifest_appears_in_system_block(tmp_path: Path) -> None:
    _write_skill(tmp_path, "code-review", "code-review", "reviews pull requests")
    _write_skill(tmp_path, "graphify", "graphify", "builds knowledge graphs")
    (tmp_path / "broken").mkdir()
    (tmp_path / "broken" / "SKILL.md").write_text("---\nname: [unclosed\n---\n", encoding="utf-8")
    session = _session_with_manifest(tmp_path)
    messages = session.to_llm_messages()
    system_content = messages[0]["content"]
    assert messages[0]["role"] == "system"
    assert "# Available Skills" in system_content
    assert "- code-review: reviews pull requests" in system_content
    assert "- graphify: builds knowledge graphs" in system_content
    assert "broken" not in system_content  # malformed skill skipped by discovery


def test_manifest_rendered_after_environment_and_project_instructions(tmp_path: Path) -> None:
    _write_skill(tmp_path, "solo", "solo", "a skill")
    session = _session_with_manifest(tmp_path)
    content = session.to_llm_messages()[0]["content"]
    assert content.index("# Available Skills") > content.index("# Environment")
    assert content.index("# Available Skills") > content.index("# Project Instructions")


def test_no_valid_skills_omits_section(tmp_path: Path) -> None:
    # empty dir
    session = _session_with_manifest(tmp_path)
    content = session.to_llm_messages()[0]["content"]
    assert "# Available Skills" not in content
    # explicit None and empty string behave identically (D-13)
    session.skill_manifest = None
    assert "# Available Skills" not in session.to_llm_messages()[0]["content"]
    session.skill_manifest = ""
    assert "# Available Skills" not in session.to_llm_messages()[0]["content"]


def test_manifest_stable_across_calls(tmp_path: Path) -> None:
    """D-08: the section is rebuilt per call — content is identical each turn."""
    _write_skill(tmp_path, "solo", "solo", "a skill")
    session = _session_with_manifest(tmp_path)
    first = session.to_llm_messages()[0]["content"]
    second = session.to_llm_messages()[0]["content"]
    assert first == second


def test_manifest_never_serialized_to_snapshot(tmp_path: Path) -> None:
    """The JSONL session file must never carry the manifest (Phase 13 completes the
    persist plumbing; this guard proves the field is non-serialized now)."""
    _write_skill(tmp_path, "solo", "solo", "a skill")
    session = _session_with_manifest(tmp_path)
    session.to_llm_messages()  # manifest is live in the system block
    assert "skill_manifest" not in session.to_snapshot_meta()
