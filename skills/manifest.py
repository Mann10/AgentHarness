from __future__ import annotations

import logging
import os
from collections.abc import Sequence

from skills.models import SkillInfo

logger = logging.getLogger(__name__)

DEFAULT_MAX_CHARS = 1500  # D-09: Claude Code's ~1,500-char listing cap precedent
TRUNCATION_MARKER = "…"   # D-10: ellipsis marker on every trimmed description
_ENV_VAR = "SKILL_MANIFEST_MAX_CHARS"


def manifest_max_chars(env: dict[str, str] | None = None) -> int:
    """Resolve the character budget: SKILL_MANIFEST_MAX_CHARS or 1500 (D-09).

    Non-numeric or non-positive values fall back to the default.
    """
    raw = (env if env is not None else os.environ).get(_ENV_VAR, "")
    try:
        value = int(raw)
    except (TypeError, ValueError):
        return DEFAULT_MAX_CHARS
    return value if value > 0 else DEFAULT_MAX_CHARS


def _sanitize_description(description: str) -> str:
    """D-14: strip newlines/control chars so one bad description can't corrupt
    the manifest block for every other skill (research P-07 sub-case).
    Newlines/tabs are CONVERTED to single spaces (the D-14 embedding
    contract: 'line1\nline2\ttext' must embed as 'line1 line2 text'), then
    remaining control chars (ord < 32, DEL 127) are removed and whitespace
    runs collapse — the result is always one line."""
    replaced = description.replace("\r", " ").replace("\n", " ").replace("\t", " ")
    cleaned = "".join(ch for ch in replaced if ord(ch) >= 32 and ord(ch) != 127)
    return " ".join(cleaned.split())


def _render(ordered: Sequence[SkillInfo], descs: dict[str, str]) -> str:
    lines = [f"- {s.name}: {descs[s.name]}" for s in ordered]
    return "# Available Skills\n" + "\n".join(lines)


def build_manifest_text(
    entries: Sequence[SkillInfo], *, max_chars: int | None = None
) -> str | None:
    """Assemble the `# Available Skills` section (D-11).

    Returns None for an empty entry list (D-13 — the caller omits the
    section; no "(none)" placeholder). Descriptions are sanitized (D-14).
    The budget is character-based (D-09) and measured on the ENTIRE rendered
    section. When over budget, the longest descriptions are trimmed first
    (tie-break: name ascending) until everything fits — whole skills are
    never dropped (D-10); every trimmed description ends with the ellipsis
    marker and is logged with a warning naming the skill. Never raises.
    """
    if not entries:
        return None
    budget = max_chars if max_chars is not None else manifest_max_chars()
    ordered = sorted(entries, key=lambda s: s.name)
    descs = {s.name: _sanitize_description(s.description) for s in ordered}
    text = _render(ordered, descs)
    min_len = len(TRUNCATION_MARKER) + 1  # a trimmed desc can't shrink below this
    trimmed: list[str] = []
    while len(text) > budget:
        candidates = [s for s in ordered if len(descs[s.name]) > min_len]
        if not candidates:
            break  # D-10: accept the (still over-budget) manifest — never drop skills
        target = min(candidates, key=lambda s: (-len(descs[s.name]), s.name))
        current = descs[target.name]
        shrink_to = (len(current) - len(TRUNCATION_MARKER)) // 2
        if shrink_to < 1:
            shrink_to = 1
        descs[target.name] = current[:shrink_to].rstrip() + TRUNCATION_MARKER
        if target.name not in trimmed:
            trimmed.append(target.name)
        text = _render(ordered, descs)
    for name in sorted(trimmed):
        logger.warning("[skills] manifest cap hit — description trimmed: %s", name)
    return text
