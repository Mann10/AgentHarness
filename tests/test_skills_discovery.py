from __future__ import annotations

from pathlib import Path

import pytest

from skills.discovery import discover_skills, parse_skill_entry

SKILL_TPL = "---\nname: {name}\ndescription: {description}\n---\n\n# body\n"


def _write_skill(root: Path, folder: str, body: str) -> Path:
    d = root / folder
    d.mkdir(parents=True, exist_ok=True)
    (d / "SKILL.md").write_text(body, encoding="utf-8")
    return d


@pytest.fixture
def skills_dir(tmp_path: Path) -> Path:
    return tmp_path / "skills"


def test_valid_skill_parsed(skills_dir: Path) -> None:
    d = _write_skill(skills_dir, "graphify", SKILL_TPL.format(name="graphify", description="build graphs"))
    entry = parse_skill_entry(d)
    assert entry is not None
    assert entry.name == "graphify"
    assert entry.description == "build graphs"
    assert entry.path == d
    assert entry.allowed_tools == ()


def test_dir_without_skill_md_returns_none(skills_dir: Path, caplog) -> None:
    d = skills_dir / "empty-dir"
    d.mkdir(parents=True)
    assert parse_skill_entry(d) is None
    assert "no SKILL.md" in caplog.text


def test_non_utf8_file_returns_none(skills_dir: Path, caplog) -> None:
    d = skills_dir / "latin1"
    d.mkdir(parents=True)
    (d / "SKILL.md").write_bytes(b"---\nname: caf\xe9\n---\n")  # invalid utf-8
    assert parse_skill_entry(d) is None
    assert "unreadable" in caplog.text


def test_missing_name_returns_none(skills_dir: Path, caplog) -> None:
    d = _write_skill(skills_dir, "noname", "---\ndescription: no name here\n---\n")
    assert parse_skill_entry(d) is None
    assert "name" in caplog.text


def test_missing_description_returns_none(skills_dir: Path, caplog) -> None:
    d = _write_skill(skills_dir, "nodesc", "---\nname: nodesc\n---\n")
    assert parse_skill_entry(d) is None
    assert "description" in caplog.text


def test_broken_yaml_returns_none(skills_dir: Path, caplog) -> None:
    d = _write_skill(skills_dir, "broken", "---\nname: [unclosed\n---\n")
    assert parse_skill_entry(d) is None
    assert "name" in caplog.text


def test_allowed_tools_valid_list_kept(skills_dir: Path) -> None:
    body = '---\nname: code-review\ndescription: reviews code\nallowed-tools:\n  - read_file\n  - bash\n---\n'
    d = _write_skill(skills_dir, "code-review", body)
    entry = parse_skill_entry(d)
    assert entry is not None
    assert entry.allowed_tools == ("read_file", "bash")


def test_allowed_tools_malformed_dropped_skill_kept(skills_dir: Path, caplog) -> None:
    body = '---\nname: bad-tools\ndescription: x\nallowed-tools: "not a list"\n---\n'
    d = _write_skill(skills_dir, "bad-tools", body)
    entry = parse_skill_entry(d)
    assert entry is not None  # D-16: skill kept
    assert entry.allowed_tools == ()  # field dropped
    assert "allowed-tools" in caplog.text


def test_allowed_tools_bad_shape_dropped(skills_dir: Path, caplog) -> None:
    body = '---\nname: bad-shape\ndescription: x\nallowed-tools:\n  - "has space"\n  - has-hyphen\n---\n'
    d = _write_skill(skills_dir, "bad-shape", body)
    entry = parse_skill_entry(d)
    assert entry is not None
    assert entry.allowed_tools == ()  # neither passes the D-15 shape
    assert "allowed-tools" in caplog.text


def test_duplicate_names_first_wins(skills_dir: Path, caplog) -> None:
    _write_skill(skills_dir, "a-dup", SKILL_TPL.format(name="dup", description="first body"))
    _write_skill(skills_dir, "b-dup", SKILL_TPL.format(name="dup", description="second body"))
    result = discover_skills(skills_dir)
    assert [s.name for s in result] == ["dup"]
    assert result[0].description == "first body"  # alphabetical first-wins
    assert "shadowed" in caplog.text
    assert "b-dup" in caplog.text  # warning names the shadowed skill


def test_frontmatter_name_wins_over_folder_name(skills_dir: Path, caplog) -> None:
    d = _write_skill(skills_dir, "mismatched-folder", SKILL_TPL.format(name="real-name", description="x"))
    result = discover_skills(skills_dir)
    assert [s.name for s in result] == ["real-name"]
    assert "differs from folder name" in caplog.text


def test_case_only_mismatch_silent_on_win32(skills_dir: Path, monkeypatch) -> None:
    monkeypatch.setattr("skills.discovery.os.name", "nt")
    _write_skill(skills_dir, "MySkill", SKILL_TPL.format(name="myskill", description="x"))
    result = discover_skills(skills_dir)
    assert [s.name for s in result] == ["myskill"]  # treated as a match (D-06)


def test_dedupe_key_posix_case_sensitive() -> None:
    """D-06 posix branch at unit level. NTFS cannot physically host both
    'Foo' and 'foo' folders (they resolve to one directory and the second
    SKILL.md would overwrite the first), so the case-sensitivity decision
    is tested through the pure _dedupe_key helper instead of the
    filesystem — distinct keys mean discover_skills keeps both entries."""
    from skills.discovery import _dedupe_key

    assert _dedupe_key("Foo", case_insensitive=False) == "Foo"
    assert _dedupe_key("foo", case_insensitive=False) == "foo"  # posix: distinct keys -> both kept
    assert _dedupe_key("Foo", case_insensitive=True) == "foo"   # win32: same key -> dedupe (D-06)


def test_missing_root_returns_empty(tmp_path: Path) -> None:
    assert discover_skills(tmp_path / "does-not-exist") == []


def test_root_with_only_files_returns_empty(skills_dir: Path) -> None:
    skills_dir.mkdir(parents=True, exist_ok=True)
    (skills_dir / "README.md").write_text("not a skill", encoding="utf-8")
    assert discover_skills(skills_dir) == []


def test_discovery_skips_malformed_never_raises(skills_dir: Path) -> None:
    _write_skill(skills_dir, "ok", SKILL_TPL.format(name="ok", description="fine"))
    _write_skill(skills_dir, "broken", "---\nname: [unclosed\n---\n")
    (skills_dir / "empty").mkdir()
    result = discover_skills(skills_dir)  # must not raise
    assert [s.name for s in result] == ["ok"]
