from __future__ import annotations

import logging
import os
from pathlib import Path

from skills.frontmatter import parse_skill_doc
from skills.models import SkillInfo

logger = logging.getLogger(__name__)

_TOOL_NAME_CHARS = set(
    "abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789_"
)


def _is_valid_tool_name(value: str) -> bool:
    """D-15 shape: non-empty, letters/digits/underscore only."""
    return bool(value) and all(c in _TOOL_NAME_CHARS for c in value)


def _dedupe_key(name: str, *, case_insensitive: bool) -> str:
    """D-06: dedupe keys are case-insensitive on win32 (NTFS) and
    case-sensitive elsewhere — 'Foo' and 'foo' collide on win32 but stay
    distinct on posix. Kept as a pure helper so both branches are
    unit-testable without creating case-distinct directories (which NTFS
    cannot host)."""
    return name.lower() if case_insensitive else name


def parse_skill_entry(skill_dir: Path) -> SkillInfo | None:
    """Parse + validate one skill directory (D-03 skip-and-warn). Never raises.

    Returns None on every malformed class: no SKILL.md, unreadable/non-UTF8
    file, broken YAML, missing/invalid frontmatter name or description.
    D-05: frontmatter `name` is authoritative — a folder-name mismatch warns
    but never skips. D-06: on win32 a case-only mismatch is treated as a
    match (silent). D-07: any non-empty name is accepted. D-15/D-16:
    allowed-tools shape-validated; malformed -> field dropped, skill kept.
    """
    skill_file = skill_dir / "SKILL.md"
    if not skill_file.is_file():
        logger.warning("[skills] skip %s: no SKILL.md", skill_dir)
        return None
    try:
        text = skill_file.read_text(encoding="utf-8")
    except (OSError, UnicodeDecodeError) as e:
        logger.warning("[skills] skip %s: unreadable SKILL.md: %s", skill_dir, e)
        return None
    meta, _body = parse_skill_doc(text)

    name = meta.get("name")
    if not isinstance(name, str) or not name.strip():
        logger.warning("[skills] skip %s: missing or invalid frontmatter 'name'", skill_dir)
        return None
    name = name.strip()  # D-07 lenient: any non-empty string is accepted

    description = meta.get("description")
    if not isinstance(description, str) or not description.strip():
        logger.warning("[skills] skip %s: missing or invalid frontmatter 'description'", skill_dir)
        return None

    # D-05/D-06: frontmatter name is authoritative; folder is a container.
    folder_name = skill_dir.name
    if name != folder_name:
        case_only = name.lower() == folder_name.lower()
        if case_only and os.name == "nt":
            pass  # D-06: NTFS case-insensitive — no warning on win32
        else:
            logger.warning(
                "[skills] %s: frontmatter 'name' (%r) differs from folder name (%r) "
                "— using frontmatter name",
                skill_dir, name, folder_name,
            )

    allowed_tools: tuple[str, ...] = ()
    raw_tools = meta.get("allowed-tools")
    if raw_tools is not None:
        if isinstance(raw_tools, list) and all(
            isinstance(t, str) and _is_valid_tool_name(t) for t in raw_tools
        ):
            allowed_tools = tuple(raw_tools)
        else:
            # D-16: broken optional field never hides the skill
            logger.warning(
                "[skills] %s: malformed 'allowed-tools' dropped (skill kept)", skill_dir
            )
    return SkillInfo(name=name, description=description, path=skill_dir, allowed_tools=allowed_tools)


def discover_skills(root: Path) -> list[SkillInfo]:
    """One-pass deterministic discovery over root/*/SKILL.md (D-08).

    D-04: duplicate names resolve first-wins over the deterministic sort —
    the shadowed skill is named in a warning. D-06: dedupe keys are
    case-insensitive on win32 (NTFS) and case-sensitive elsewhere.
    Iteration order is sorted by folder name (case-insensitive) so first-wins
    is reproducible across platforms. Never raises (P-07).
    """
    if not root.is_dir():
        return []
    seen: dict[str, SkillInfo] = {}
    case_insensitive = os.name == "nt"  # D-06: NTFS is case-insensitive
    for skill_dir in sorted(root.iterdir(), key=lambda p: p.name.lower()):
        if not skill_dir.is_dir():
            continue
        entry = parse_skill_entry(skill_dir)
        if entry is None:
            continue
        key = _dedupe_key(entry.name, case_insensitive=case_insensitive)  # D-06
        previous = seen.get(key)
        if previous is None:
            seen[key] = entry
        else:
            logger.warning(
                "[skills] '%s' (%s) shadowed by first-wins duplicate '%s' (%s)",
                entry.name, skill_dir, previous.name, previous.path,
            )
    return sorted(seen.values(), key=lambda s: s.name)
