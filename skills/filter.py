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
