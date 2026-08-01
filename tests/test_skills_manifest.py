from __future__ import annotations

from pathlib import Path

from skills.manifest import DEFAULT_MAX_CHARS, TRUNCATION_MARKER, build_manifest_text, manifest_max_chars
from skills.models import SkillInfo


def _skill(name: str, description: str) -> SkillInfo:
    return SkillInfo(name=name, description=description, path=Path(name))


def test_empty_entries_returns_none() -> None:
    assert build_manifest_text([]) is None


def test_fits_within_budget_no_marker() -> None:
    result = build_manifest_text(
        [_skill("a", "alpha tool"), _skill("b", "beta tool")], max_chars=1500
    )
    assert result is not None
    assert result.startswith("# Available Skills\n")
    assert "- a: alpha tool" in result
    assert "- b: beta tool" in result
    assert TRUNCATION_MARKER not in result


def test_manifest_never_exceeds_budget() -> None:
    entries = [_skill(f"skill-{i}", "d" * 200) for i in range(30)]
    result = build_manifest_text(entries, max_chars=500)
    assert result is not None
    assert len(result) <= 500


def test_all_skills_stay_listed_when_trimmed() -> None:
    entries = [_skill(f"skill-{i}", "d" * 200) for i in range(30)]
    result = build_manifest_text(entries, max_chars=500)
    assert result is not None
    for i in range(30):
        assert f"- skill-{i}:" in result  # D-10: whole skills never dropped


def test_trimmed_descriptions_get_marker_and_warning(caplog) -> None:
    entries = [_skill(f"skill-{i}", "d" * 200) for i in range(30)]
    result = build_manifest_text(entries, max_chars=500)
    assert result is not None
    assert TRUNCATION_MARKER in result
    assert "description trimmed" in caplog.text
    assert "skill-0" in caplog.text  # warning names trimmed skills


def test_trim_selection_is_deterministic() -> None:
    entries = [_skill(f"skill-{i}", "d" * 200) for i in range(30)]
    a = build_manifest_text(entries, max_chars=500)
    b = build_manifest_text(list(reversed(entries)), max_chars=500)
    assert a == b  # input order does not affect output


def test_description_sanitized_for_embedding() -> None:
    result = build_manifest_text(
        [_skill("messy", "line1\nline2\twith  spaced   text\x00\x1b")], max_chars=1500
    )
    assert result is not None
    assert "\n" not in result.split("- messy:", 1)[1]
    assert "line1 line2 with spaced text" in result


def test_env_var_override(monkeypatch) -> None:
    monkeypatch.setenv("SKILL_MANIFEST_MAX_CHARS", "100")
    assert manifest_max_chars() == 100
    monkeypatch.delenv("SKILL_MANIFEST_MAX_CHARS")
    assert manifest_max_chars() == DEFAULT_MAX_CHARS
    monkeypatch.setenv("SKILL_MANIFEST_MAX_CHARS", "not-a-number")
    assert manifest_max_chars() == DEFAULT_MAX_CHARS


def test_budget_applies_to_entire_section() -> None:
    result = build_manifest_text([_skill("a", "x" * 300)], max_chars=100)
    assert result is not None
    assert len(result) <= 100
