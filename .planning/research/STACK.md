# Stack Research

**Domain:** Progressive-disclosure Skills System for a Python 3.12 async agent harness (v1.1 milestone)
**Researched:** 2026-08-01
**Confidence:** HIGH

## Summary of the Problem

The harness already ships a validated backend (Agent loop, ToolRegistry with `__builtin__` local provider + MCP providers, ConversationContext with token counting + summarization, JSONL sessions, tiktoken-based `count_tokens`). The Skills milestone adds: SKILL.md discovery + frontmatter parsing, a manifest injected into the system prompt, a `read_skill` tool, a `/skill` slash command, and `allowed-tools` filtering.

**The research conclusion up front: this milestone needs exactly ONE new runtime dependency — PyYAML — plus a small internal `skills/` package. No DB, no file watcher, no schema validator, no token-counting library, no ruamel.yaml, no python-frontmatter (initially).** Everything else reuses existing machinery.

## Recommended Stack

### Core Technologies

| Technology | Version | Purpose | Why Recommended |
|------------|---------|---------|-----------------|
| PyYAML | 6.0.3 (2025-09-25) | Parse YAML frontmatter in SKILL.md files | Only new runtime dep. `yaml.safe_load` uses SafeLoader → safe for untrusted user-authored files. Tiny, ubiquitous, production-stable. Verified on PyPI: cp312 win_amd64 wheels exist, Python >=3.8. Read-only parsing means the round-trip/comment-preservation features of ruamel.yaml are dead weight. |
| tiktoken (existing) | >=0.7.0 (already in requirements.txt) | Token-count the manifest against its budget | `BaseLLMClient.count_tokens()` (llm/base.py) already wraps tiktoken with a `len(text.split())` fallback. The manifest budget uses this same call — consistency with context token accounting for free, zero new code paths, zero new deps. |
| Python stdlib (pathlib, dataclasses) | 3.12 | Discovery scan, Skill model, manifest assembly | `os.scandir`/`Path.iterdir()` over `.agentharness/skills/*/SKILL.md` is O(dirs); a dozen folders scans in microseconds. No index, no cache. |

### Supporting Libraries

| Library | Version | Purpose | When to Use |
|---------|---------|---------|-------------|
| python-frontmatter | 1.3.0 | Parse YAML/JSON/TOML frontmatter into metadata + content | ONLY if edge cases multiply (multi-format frontmatter, Jekyll-style variance, write-back needs). Wraps PyYAML, so it's a one-line pip add later. Not needed for the fixed `name`/`description`/`allowed-tools` schema — a ~20-line internal splitter + `safe_load` covers it (see "Frontmatter splitter" pattern below). |
| watchdog | — | File-system watching | NOT USED. See What NOT to Use. |

### Development Tools

| Tool | Purpose | Notes |
|------|---------|-------|
| (none new) | — | The project's pytest suite + existing TUI typecheck/build pipeline covers this. New `skills/` package gets plain pytest unit tests (frontmatter parser, manifest budgeting, provider dispatch). No mock/faker libs needed — use `tmp_path` fixtures. |

## Installation

```bash
# One new runtime dependency for this milestone
pip install "PyYAML>=6.0.3"

# requirements.txt addition:
#   PyYAML>=6.0.3
```

## Frontmatter splitter pattern (internal, ~20 lines)

Hand-rolled because the schema is fixed and the harness must never crash on a bad file:

```python
import yaml

def parse_skill_doc(text: str) -> tuple[dict, str]:
    """Return (metadata, body). Missing/malformed frontmatter -> ({}, text)."""
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
    return meta, "".join(lines[end + 1 :]).lstrip("\n")
```

- Handles CRLF (`\r\n`), missing closing `---`, non-dict YAML, and YAML errors → all degrade to `({}, body)`.
- Description fallback for the manifest when `description` is absent: first non-empty body paragraph, truncated (e.g. 200 chars).
- This splitter belongs in the new `skills/` package (e.g. `skills/frontmatter.py`), unit-tested with `tmp_path`-written SKILL.md fixtures.

## Integration Points (existing code, verified by reading)

| File | Change Needed | Details |
|------|---------------|---------|
| `tool/registry.py` | **NO structural change** | `ToolRegistry.add_provider(name, provider, namespace)` (registry.py:34) already supports a third provider type. A `SkillToolProvider` implementing the `ToolProvider` Protocol (tool/models.py:7) slots in: `fetch_tools()` → `[read_skill]`, `call_tool()` → store lookup. `list_tools()`/`call_tool()` dispatch by name with zero edits. |
| `main.py:302-303` + `harness/runtime.py` | Wiring | Register alongside the existing `registry.add_provider("__builtin__", local_provider)` pattern: build the `SkillStore` once, `registry.add_provider("skills", SkillToolProvider(store))`. Same call in both the REPL path (main.py) and the runtime path (runtime.py). |
| `session/models.py` | Manifest injection | `_build_system_prompt()` (models.py:63) is the single choke point that already composes system_prompt + AGENTS.md + CWD. Append the manifest block here. `Session.create()` gains a `skills_manifest: str = ""` param; **`from_events()`/restore path must also re-inject** (SessionManager holds the SkillStore — restored sessions get the manifest from the store, not from JSONL, since JSONL only stores the base `system_prompt`). Flag for plan phase. |
| `agent/core.py` | read_skill system-message injection | `context.add_tool_message()` is generic; for `read_skill` results the body must land as a **system-role** message (SKL-05). Small branch in the result loop: if `tc.name == "read_skill"`, `await self._context.add_message(Message(role="system", content=skill_body))` and add a short ack tool message. `allowed-tools` filtering also lands here: filter `self._registry.list_tools()` (core.py:108) against the union of loaded skills' allowed sets. |
| `context/context.py` | **NO change** | `Message` accepts any role; `to_llm_messages()` passes `role` through; summarization already skips `role == "system"` (context.py:88); `to_events()` serializes any role to JSONL. **Loaded skills survive summarization and persist across restarts by existing design** — this is the strongest argument for system-role persistence. |
| `config.py` | Optional | `skills_dir` env with default `.agentharness/skills/` (consistent with `session/store.py:35` using `Path.cwd() / ".agentharness"`). |

## Token Counting for the Manifest Budget

- Use the existing `count_tokens` callable (tiktoken, llm/base.py:49) — same function that budgets the conversation context, so manifest math is consistent with context accounting.
- Budget constant, e.g. `SKILL_MANIFEST_MAX_TOKENS = 800` (tunable via env). Assembly: iterate discovered skills in deterministic order (alphabetical by folder name), render each entry as `- <name>: <description>`, accumulate tokens, **stop adding entries once the budget is exceeded** (first-wins). Optionally pre-truncate descriptions to ~120 chars at authoring-convention level.
- The manifest is a session-scoped snapshot: rebuild at session creation, never mid-session (see file-watching anti-decision).

## Alternatives Considered

| Recommended | Alternative | When to Use Alternative |
|-------------|-------------|-------------------------|
| PyYAML 6.0.3 + internal splitter | python-frontmatter 1.3.0 | If skills need multi-format frontmatter (JSON/TOML), write-back, or Jekyll-style variance. Cheap later add — it just wraps PyYAML. |
| PyYAML 6.0.3 | ruamel.yaml 0.18.17 | If skills ever need to preserve comments/formatting on write-back (e.g. a skill authoring/editing UI — explicitly out of scope for v1.1). Read-only parse makes YAML 1.2 + round-trip features pointless. |
| Startup-only discovery | watchdog (file watching) | If users expect mid-session skill hot-reload with zero action. Requires native FS watchers (ReadDirectoryChangesW on Windows), background threads/event-loop integration, and system-prompt re-injection — a disproportional cost for a manifest that is a fixed session snapshot anyway. |
| Filesystem-only store | SQLite/JSON skill index | If the skill corpus grows to thousands with complex queries. At dozens of folders, a persisted index is a staleness bug farm with zero latency benefit. |

## What NOT to Use

| Avoid | Why | Use Instead |
|-------|-----|-------------|
| ruamel.yaml | Round-trip/comment preservation is irrelevant for read-only frontmatter; heavier; YAML 1.2 features unused; top-level `safe_load`/`load` deprecated in favor of the `YAML()` class API (PendingDeprecationWarning). | PyYAML 6.0.3 `safe_load` |
| watchdog (or any FS watcher) | Progressive disclosure means the manifest is a fixed session snapshot — mid-session changes wouldn't surface without re-injecting the system prompt. Also: `read_skill` resolves by name **at call time**, so even a skill added mid-session is readable on demand even if absent from the manifest. Windows watcher integration (background threads + native events) is a disproportional complexity sink. | Startup-only scan + `/skill reload`-style restart or next session |
| SQLite / JSON index / any skill-store DB | Zero benefit at this scale; persisted-index staleness bugs; session store is already JSONL in `.agentharness/`. | Direct filesystem scan per session (O(dirs)) |
| python-frontmatter (initially) | Adds a dependency for what a 20-line splitter + `safe_load` does; its value (multi-format handlers, write-back, Post object model) is unused. | Internal splitter (pattern above); adopt the lib only if frontmatter variance grows |
| pydantic / cerberus / any schema validator | Frontmatter is 2-3 optional fields (`name`, `description`, `allowed-tools`); validation is a handful of `isinstance` checks. | Inline validation in `skills/models.py` (Skill dataclass) |
| A new token-counting library | `count_tokens` with tiktoken already exists and is used for context budgeting. | Existing `count_tokens` callable |
| Any change to `context/context.py` | System-role messages already flow through, survive summarization (context.py:88), and serialize to JSONL. | Zero changes |

## Stack Patterns by Variant

**If running REPL mode (main.py):**
- Register the skills provider next to `registry.add_provider("__builtin__", local_provider)` (main.py:302-303); pass `skills_manifest` into `Session.create()` via the same path `system_prompt` flows (main.py:85).

**If running runtime/TUI mode (harness/runtime.py):**
- Same registration call in the RuntimeAPI init path (runtime.py:14 already imports `register_builtin_tools`); SessionManager (harness/session_manager.py:40) forwards `skills_manifest` into `Session.create(**kwargs)` — the existing kwargs-passing design makes this a one-line addition.

**If a skill has `allowed-tools`:**
- No registry change — filter `registry.list_tools()` output in `agent/core.py` per iteration once that skill is loaded; unloaded skills expose all tools (progressive disclosure default).

## Version Compatibility

| Package A | Compatible With | Notes |
|-----------|-----------------|-------|
| PyYAML 6.0.3 | Python 3.12 (project std) | Verified on PyPI (released 2025-09-25): cp312 win_amd64/win32 wheels, `requires-python >=3.8`. No C-extension requirement if wheels unavailable (pure-Python fallback exists). |
| PyYAML 6.0.3 | tiktoken >=0.7.0, openai >=1.0.0, mcp >=1.27 | Independent of all existing deps — no version coupling. |
| python-frontmatter 1.3.0 (if adopted) | PyYAML | Its only dependency is PyYAML; requires the splitter be swapped for `frontmatter.parse()` — trivial migration. |
| tiktoken >=0.7.0 | config.model (llm/base.py:53) | Existing `encoding_for_model` requires a known model name; the fallback (`len(text.split())`) already covers unknown models — manifest budgeting inherits the same resilience. |

## Sources

- [PyPI: PyYAML 6.0.3](https://pypi.org/project/PyYAML/6.0.3/) — version, release date (2025-09-25), cp312 wheels, requires-python. HIGH confidence.
- [Context7: /yaml/pyyaml](https://github.com/yaml/pyyaml/blob/main/_autodocs/00-START-HERE.md) — `safe_load`/`safe_load_all` API for untrusted input. HIGH confidence.
- [Context7: /pycontribs/ruamel-yaml](https://github.com/pycontribs/ruamel-yaml/blob/master/README.md) — YAML() class API, deprecated top-level `load`/`safe_load`. HIGH confidence.
- [PyPI: ruamel.yaml 0.18.17 / 0.19.0](https://pypi.org/project/ruamel.yaml/0.18.17/) — current versions. HIGH confidence.
- [PyPI + ReadTheDocs: python-frontmatter 1.3.0](https://python-frontmatter.readthedocs.io/) — `frontmatter.parse()` returns (metadata, content); YAMLHandler safe-mode default. HIGH confidence.
- [Project source: llm/base.py, tool/registry.py, tool/local_provider.py, context/context.py, session/models.py, main.py, harness/runtime.py] — verified integration points (no changes needed in registry.py / context.py). HIGH confidence (read directly).

---
*Stack research for: AgentHarness v1.1 Skills System*
*Researched: 2026-08-01*
