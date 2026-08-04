from __future__ import annotations

import yaml


def parse_skill_doc(text: str) -> tuple[dict, str]:
    """Return (metadata, body). Missing/malformed frontmatter -> ({}, text).

    Handles CRLF. Never raises: YAML errors, missing delimiters, and
    non-dict YAML all degrade to the empty-metadata fallback (P-07 / D-03).
    Uses yaml.safe_load (SafeLoader) — never yaml.load (T-12-01).
    """
    if not text.startswith("---"):
        return {}, text
    lines = text.splitlines(keepends=True)
    end = None
    for i, line in enumerate(lines[1:], start=1):
        if line.rstrip("\r\n") == "---":
            end = i
            break
    if end is None:
        return {}, text
    try:
        meta = yaml.safe_load("".join(lines[1:end])) or {}
    except yaml.YAMLError:
        meta = {}
    if not isinstance(meta, dict):
        meta = {}
    # Strip the blank line after the closing delimiter for BOTH LF and CRLF
    # (a lone lstrip("\n") leaves the "\r" of a CRLF blank line in the body).
    return meta, "".join(lines[end + 1 :]).lstrip("\r\n")
