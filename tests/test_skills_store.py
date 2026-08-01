"""Contract + traversal tests for the SkillStore (Plan 14-01).

The traversal suite is the phase's Wave 0 scaffold: every vector in the
security checklist ships in the same wave as the tool itself (ROADMAP
success criterion 3, ASVS V9 path-traversal). Vectors are parametrized so
the suite reads as a security checklist.

Guard contract (D-10/D-11/D-12):
  read_path canonicalizes (skill_dir / rel).resolve() and requires
  p.is_relative_to(skill_dir.resolve()); any escape raises ValueError
  naming BOTH the skill and the rejected path.
"""

from __future__ import annotations

import os
from pathlib import Path

import pytest

from skills.store import SkillStore

SKILL_FRONTMATTER = (
    "---\n"
    "name: demo-greeter\n"
    "description: A demo skill\n"
    "---\n"
    "\n"
    "# Demo\n"
    "\n"
    "Do the thing.\n"
)
GUIDE_TEXT = "# Guide\n\nHow to use the greeter.\n"
LOGO_TEXT = "fake logo bytes\n"


@pytest.fixture
def skill_dir(tmp_path: Path) -> Path:
    """A tmp skills root holding one valid skill with bundled resources."""
    d = tmp_path / "skills" / "demo-greeter"
    d.mkdir(parents=True)
    (d / "SKILL.md").write_text(SKILL_FRONTMATTER, encoding="utf-8")
    refs = d / "references"
    refs.mkdir()
    (refs / "guide.md").write_text(GUIDE_TEXT, encoding="utf-8")
    assets = d / "assets"
    assets.mkdir()
    (assets / "logo.txt").write_text(LOGO_TEXT, encoding="utf-8")
    return d


# --- index: frontmatter-name lookup (T-14-01) -------------------------------


def test_lookup_resolves_frontmatter_name(skill_dir: Path) -> None:
    store = SkillStore(skill_dir.parent)
    info = store.lookup("demo-greeter")
    assert info.name == "demo-greeter"
    assert info.path == skill_dir


def test_lookup_case_insensitive_on_win32(skill_dir: Path, monkeypatch) -> None:
    # D-06: matching is case-insensitive on win32 (NTFS). The store reads
    # os.name at construction — force the win32 branch on any platform.
    monkeypatch.setattr("skills.store.os.name", "nt")
    store = SkillStore(skill_dir.parent)
    assert store.lookup("DEMO-GREETER").name == "demo-greeter"


def test_lookup_case_sensitive_on_posix(skill_dir: Path, monkeypatch) -> None:
    # Posix branch of the same decision: distinct case is a different name.
    monkeypatch.setattr("skills.store.os.name", "posix")
    store = SkillStore(skill_dir.parent)
    with pytest.raises(KeyError):
        store.lookup("DEMO-GREETER")


def test_lookup_unknown_name_raises_keyerror(skill_dir: Path) -> None:
    store = SkillStore(skill_dir.parent)
    with pytest.raises(KeyError):
        store.lookup("no-such-skill")


# --- load: body after frontmatter -------------------------------------------


def test_load_returns_body_markdown(skill_dir: Path) -> None:
    store = SkillStore(skill_dir.parent)
    body = store.load("demo-greeter")
    assert body.startswith("# Demo")
    assert "Do the thing." in body
    assert "name: demo-greeter" not in body  # frontmatter stripped


# --- read_path: in-bounds reads ----------------------------------------------


def test_read_path_happy_path_references(skill_dir: Path) -> None:
    store = SkillStore(skill_dir.parent)
    assert store.read_path("demo-greeter", "references/guide.md") == GUIDE_TEXT


def test_read_path_in_bounds_after_traversal_vectors(skill_dir: Path) -> None:
    """The guard must not over-reject: after every universal escape attempt
    raises, a legitimate in-bounds read still succeeds."""
    store = SkillStore(skill_dir.parent)
    for rel in ("../secrets.txt", "../../config.py", "/etc/passwd"):
        with pytest.raises(ValueError):
            store.read_path("demo-greeter", rel)
    assert store.read_path("demo-greeter", "assets/logo.txt") == LOGO_TEXT


# --- read_path: traversal suite (T-14-02, D-12) ------------------------------

TRAVERSAL_VECTORS = [
    pytest.param("../secrets.txt", id="dotdot-slash"),
    pytest.param("../../config.py", id="double-dotdot"),
    pytest.param("/etc/passwd", id="absolute-posix-root"),
    pytest.param(
        "..\\secrets.txt",
        id="dotdot-backslash-win32",
        marks=pytest.mark.skipif(
            os.name != "nt", reason="backslash is a filename char on posix"
        ),
    ),
    pytest.param(
        "C:\\windows\\win.ini",
        id="win32-drive-absolute",
        marks=pytest.mark.skipif(
            os.name != "nt", reason="win32 drive-path vector"
        ),
    ),
]


@pytest.mark.parametrize("rel", TRAVERSAL_VECTORS)
def test_traversal_vector_rejected(skill_dir: Path, rel: str) -> None:
    """Every escape attempt raises a clear error naming BOTH the skill and
    the rejected path — never a silent empty result (D-12)."""
    store = SkillStore(skill_dir.parent)
    with pytest.raises(ValueError) as exc:
        store.read_path("demo-greeter", rel)
    message = str(exc.value)
    assert "demo-greeter" in message  # names the skill (D-12)
    assert rel in message  # names the rejected path (D-12)


def test_symlink_escape_rejected(skill_dir: Path, tmp_path: Path) -> None:
    """D-11: a symlink/junction inside the skill dir resolving outside is
    rejected. Skipped when the platform cannot create symlinks (e.g.
    non-admin win32) — the resolve-based guard is still exercised by every
    other vector."""
    outside = tmp_path / "outside"
    outside.mkdir()
    (outside / "secrets.txt").write_text("top secret\n", encoding="utf-8")
    try:
        os.symlink(outside, skill_dir / "escaped", target_is_directory=True)
    except (OSError, NotImplementedError) as e:
        pytest.skip(f"cannot create symlinks on this platform: {e}")
    store = SkillStore(skill_dir.parent)
    with pytest.raises(ValueError) as exc:
        store.read_path("demo-greeter", "escaped/secrets.txt")
    message = str(exc.value)
    assert "demo-greeter" in message
    assert "escaped/secrets.txt" in message
