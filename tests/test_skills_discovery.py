from __future__ import annotations

from pathlib import Path

import pytest

from skills.discovery import parse_skill_entry

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
