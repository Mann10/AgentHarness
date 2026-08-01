from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True)
class SkillInfo:
    """A validated skill discovered on disk.

    name:          manifest-facing name — the frontmatter `name`, authoritative
                   over the folder name (D-05)
    description:   routing signal: what the skill does AND when to use it (D-02)
    path:          the skill's directory (the folder holding SKILL.md)
    allowed_tools: shape-validated allowed-tools (D-15); () when absent or
                   dropped as malformed (D-16)
    """

    name: str
    description: str
    path: Path
    allowed_tools: tuple[str, ...] = ()
