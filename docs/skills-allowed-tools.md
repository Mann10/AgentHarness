# Skill Allowed-Tools Combined Filter (CAP-04)

**Status:** Contract locked — Phase 15 (decided), Phase 17 (enforced)
**Decisions recorded:** D-13, D-14 (15-CONTEXT) | CAP-03 (Phase 14)

## Purpose

CAP-04 defines how multiple loaded skills' `allowed-tools` fields combine
into a single per-iteration tool filter. The semantics are **locked in
Phase 15** and shipped as pure, unit-tested functions so Phase 17 only
implements enforcement — it never re-decides the semantics.

## The Contract

### D-13 — Intersection over restricted skills

When more than one skill with an `allowed-tools` field is loaded, a tool is
retained **only if it is in EVERY loaded skill's allowed-tools list**
(set intersection over the restricted skills).

### D-14 — No `allowed-tools` = no restriction

A loaded skill with **no `allowed-tools` field** (empty tuple `()` from
`SkillInfo`, i.e. the field is absent or dropped as malformed, D-15/D-16)
**imposes no restriction** — it is treated as allowing everything and is
**excluded from the intersection computation**.

- This is NOT "allow nothing" — an empty `allowed_tools` is the
  "unrestricted" signal (skills/models.py).
- When no loaded skill restricts, the intersection is the empty set (no
  restriction to apply).

### CAP-03 — Skill tools always retained

`read_skill` / `read_skill_path` are **always retained** regardless of the
intersection — the filter projection always re-applies
`retain_read_skills()` (skills/filter.py) after the intersection.

## Contract Surfaces

| Function | File | Role |
|----------|------|------|
| `skills.filter.intersect_allowed_tools(allowed_sets: list[set[str]]) -> set[str]` | `skills/filter.py` | Pure D-13/D-14 intersection — empty sets skipped, `set()` when nothing restricts |
| `skills.filter.retain_read_skills(tools, allowed)` | `skills/filter.py` | CAP-03 retention — always keeps the skill tools |

Unit tests: `tests/test_skills_filter.py` (Phase 15).

## Enforcement Plan (Phase 17)

Phase 17 applies the projection per agent iteration:

1. Collect `allowed_tools` from every skill in `skill_state["loaded"]`.
2. `combined = intersect_allowed_tools([set(s.allowed_tools) for s in loaded])`.
3. Filter the available tool list by `combined`, then re-apply
   `retain_read_skills` (CAP-03) so the skill tools always survive.
