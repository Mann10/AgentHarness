from __future__ import annotations

from tool.models import Tool

RESERVED_SKILL_TOOLS = frozenset({"read_skill", "read_skill_path"})


def retain_read_skills(tools: list[Tool], allowed: set[str] | frozenset[str] | None) -> list[Tool]:
    """CAP-03 retention contract: the allowed-tools filter always retains the skill tools.

    allowed=None means no restriction (all tools pass). Enforcement wiring is Phase 17 —
    this pure function is the contract, unit-tested here."""
    if allowed is None:
        return list(tools)
    keep = set(allowed) | RESERVED_SKILL_TOOLS
    return [t for t in tools if t.name in keep]


def intersect_allowed_tools(allowed_sets: list[set[str]]) -> set[str]:
    """D-13/D-14 CAP-04 contract: intersection over restricted skills only.

    A skill with an empty allowed-tools set (or () tuple from SkillInfo)
    imposes NO restriction (D-14) and is excluded from the intersection.
    Returns set() when no skill restricts. read_skill/read_skill_path are
    always retained separately via retain_read_skills (CAP-03).
    Enforcement wiring is Phase 17 — this pure function is the contract."""
    restricted = [s for s in allowed_sets if s]
    return set.intersection(*restricted) if restricted else set()
