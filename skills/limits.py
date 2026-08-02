from __future__ import annotations

import os

DEFAULT_LOADED_SKILL_TOKEN_CAP = 8000  # D-12: ~8k tokens, env-overridable
_ENV_VAR = "LOADED_SKILL_TOKEN_CAP"


def loaded_skill_token_cap(env: dict[str, str] | None = None) -> int:
    """D-10/D-12: resolve the loaded-skill token budget: LOADED_SKILL_TOKEN_CAP or 8000.

    Non-numeric or non-positive values fall back to the default
    (mirrors skills/manifest.py manifest_max_chars()).
    """
    raw = (env if env is not None else os.environ).get(_ENV_VAR, "")
    try:
        value = int(raw)
    except (TypeError, ValueError):
        return DEFAULT_LOADED_SKILL_TOKEN_CAP
    return value if value > 0 else DEFAULT_LOADED_SKILL_TOKEN_CAP
