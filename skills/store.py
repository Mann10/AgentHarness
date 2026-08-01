"""SkillStore — the risky skill-dir I/O owner for the read path.

Builds a deterministic index from the Phase 12 discovery pipeline, loads
skill bodies by frontmatter name, and provides the single traversal-guarded
`read_path` (D-10/D-11/D-12) that Plan 14-02's `read_skill_path` handler and
Plan 14-03's `RuntimeAPI.load_skill()` delegate to.

Path-safety contract (T-14-02, T-14-03):
    read_path canonicalizes (skill_dir / rel).resolve() and requires
    p.is_relative_to(skill_dir.resolve()). A symlink resolving outside the
    skill dir, a `..` segment, or an absolute path all fail containment and
    raise ValueError naming the skill and the rejected path — never a silent
    empty result.
"""

from __future__ import annotations

import logging
import os
from pathlib import Path

from skills.discovery import discover_skills
from skills.frontmatter import parse_skill_doc
from skills.models import SkillInfo

logger = logging.getLogger(__name__)


class SkillStore:
    def __init__(self, root: Path) -> None:
        self._root = root
        self._case_insensitive = os.name == "nt"  # D-06: NTFS
        self._skills: dict[str, SkillInfo] = {}  # key = dedupe key
        self._reindex()

    def _key(self, name: str) -> str:
        return name.lower() if self._case_insensitive else name

    def _reindex(self) -> None:
        self._skills = {}
        for info in discover_skills(self._root):
            self._skills[self._key(info.name)] = info

    def lookup(self, name: str) -> SkillInfo:
        info = self._skills.get(self._key(name.strip()))
        if info is None:
            raise KeyError(f"Unknown skill '{name}'")  # caller formats the read_skill error
        return info

    def load(self, name: str) -> str:
        info = self.lookup(name)
        text = (info.path / "SKILL.md").read_text(encoding="utf-8")
        _meta, body = parse_skill_doc(text)
        return body.strip()

    def read_path(self, name: str, rel: str) -> str:
        info = self.lookup(name)
        base = info.path.resolve()  # D-11: canonicalize base (resolves symlinks)
        p = (info.path / rel).resolve()  # D-11: canonicalize AFTER join — defeats ../ and symlink escapes
        if not p.is_relative_to(base):
            raise ValueError(
                f"Path '{rel}' escapes skill '{name}' — only files inside the skill directory are readable"
            )  # D-12
        return p.read_text(encoding="utf-8")
