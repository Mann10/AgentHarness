"""CAP-04 combined allowed-tools intersection contract tests (Phase 15 Plan 15-03).

Covers skills.filter.intersect_allowed_tools — the D-13/D-14 pure-function
contract locked in Phase 15 for Phase 17 enforcement:

- D-13: a tool is retained only if it is in EVERY loaded skill's allowed-tools
  (intersection over the restricted skills).
- D-14: a loaded skill with an empty allowed-tools set (() tuple / set())
  imposes NO restriction — it is excluded from the intersection computation.
- Returns set() when no skill restricts.

This file mirrors the CAP-03 retain_read_skills test shape
(tests/test_skills_provider.py) — contract-before-enforcement.
"""

from __future__ import annotations

from skills.filter import intersect_allowed_tools


def test_intersect_returns_tools_common_to_all_restricted_skills() -> None:
    """D-13: intersection over restricted skills — only tools in EVERY set survive."""
    result = intersect_allowed_tools([{"echo", "ls"}, {"echo", "cat"}])
    assert result == {"echo"}


def test_intersect_skips_empty_allowed_sets() -> None:
    """D-14: an empty allowed-tools set imposes no restriction and is skipped."""
    result = intersect_allowed_tools([{"echo", "ls"}, set()])
    assert result == {"echo", "ls"}


def test_intersect_single_restriction_returns_that_set() -> None:
    """A single restricted skill yields its own allowed set (trivial intersection)."""
    result = intersect_allowed_tools([{"echo", "ls", "cat"}])
    assert result == {"echo", "ls", "cat"}


def test_intersect_disjoint_sets_returns_empty() -> None:
    """Disjoint restricted sets share no tool — the intersection is empty."""
    result = intersect_allowed_tools([{"echo"}, {"ls"}])
    assert result == set()


def test_intersect_all_unrestricted_returns_empty() -> None:
    """D-14: when every skill is unrestricted the intersection is empty (no restriction)."""
    result = intersect_allowed_tools([set(), set(), set()])
    assert result == set()


def test_intersect_empty_input_returns_empty() -> None:
    """No loaded skills → empty result."""
    result = intersect_allowed_tools([])
    assert result == set()
