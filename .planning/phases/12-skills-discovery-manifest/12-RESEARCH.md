---
phase: 12
slug: skills-discovery-manifest
status: complete
created: 2026-08-01
synthesized_from: [.planning/research/ARCHITECTURE.md, .planning/research/STACK.md, .planning/research/FEATURES.md, .planning/research/PITFALLS.md]
---

# Phase 12 — Skills Discovery & Manifest: Phase-Scoped Research Synthesis

> Phase-scoped synthesis of the project-wide v1.1 skills research (2026-08-01). All claims verified against source. This file exists because Phase 12 has no standalone gsd-phase-researcher run; the milestone research covers this phase's scope (STORE-01..05, DISC-01..02) directly.

## Objective

Users author skills as `.agentharness/skills/<name>/SKILL.md`, and the agent sees a budgeted manifest (name + description) in the system prompt each turn. Phase 12 = authoring format + one-pass discovery (skip-and-warn, first-wins) + budgeted manifest assembly + the `_build_system_prompt()` seam. Pure domain work; wiring into `main.py`/`harness/runtime.py` is Phase 14.

## Locked Decisions D-01..D-17 (from 12-CONTEXT.md — authoritative)

| ID | Rule |
|----|------|
| D-01 | Project-local storage: `.agentharness/skills/<name>/SKILL.md`, one folder per skill |
| D-02 | Frontmatter: `name` + `description` required, `allowed-tools` optional; description = routing signal (what + when) |
| D-03 | Malformed (missing/invalid frontmatter, broken YAML, empty, non-UTF8) → log warning + skip; never breaks harness |
| D-04 | Duplicate names → first-wins in deterministic sort + warning naming the shadowed skill |
| D-05 | Frontmatter `name` ≠ folder name → frontmatter name is authoritative, folder is a container; warn, do NOT skip |
| D-06 | On win32, mismatch differing only by case (MySkill vs myskill) → treated as match, no warning; case-sensitive compare only on non-win32 |
| D-07 | Name validation lenient — any non-empty name accepted; kebab-case is convention, not enforcement |
| D-08 | Manifest assembled fresh per system-prompt build (per-call rebuild = free live discovery), deterministic scan |
| D-09 | Budget is character-based (model-independent), default **1,500 chars**, configurable via `SKILL_MANIFEST_MAX_CHARS` env |
| D-10 | Over-budget → over-long descriptions truncated longest-first; whole skills never dropped; every trimmed description gets ellipsis marker + warning log |
| D-11 | Renders as `# Available Skills` heading + `- <name>: <description>` bullet lines |
| D-12 | Section appended at END of parts list in `Session._build_system_prompt()` (after AGENTS.md + CWD) |
| D-13 | No valid skills → section omitted entirely (no "(none)" placeholder) |
| D-14 | Descriptions sanitized for embedding (strip newlines/control chars) before assembly |
| D-15 | `allowed-tools` parsed + shape-validated: list of non-empty strings matching tool-name shape (letters/digits/underscore) |
| D-16 | `allowed-tools` present but malformed → skill KEPT, field DROPPED, warning logged |
| D-17 | Shape-only validation — no cross-check against tool registry at discovery; enforcement is Phase 17 |

## Stack (exactly ONE new runtime dependency)

- **PyYAML 6.0.3** → `requirements.txt` addition: `PyYAML>=6.0.3`. Install: `python -m pip install "PyYAML>=6.0.3"`. SafeLoader only (`yaml.safe_load`) — safe for untrusted user-authored files. NOT installed in this environment yet (verified 2026-08-01).
- Python 3.12.5 stdlib (`pathlib`, `dataclasses`, `logging`, `os`) for everything else. No ruamel, no python-frontmatter, no watcher, no DB, no token-counting lib (cap is chars per D-09 / P-01).

## Frontmatter splitter pattern (from STACK.md, verified shape)

`parse_skill_doc(text) -> (dict, str)` — delimiter splitter + `yaml.safe_load`. Missing `---` opener, missing closing `---`, YAML error, or non-dict YAML → degrade to `({}, text)`. Handles CRLF. This exact ~20-line function ships in `skills/frontmatter.py`.

## Codebase integration facts (verified this session)

- `session/models.py`:
  - `_build_system_prompt()` at **L63-69**: `parts = [self.system_prompt]` → appends `# Project Instructions` if `AGENTS.md` exists → appends `# Environment\nCWD: {cwd}` → `"\n\n---\n\n".join(parts)`. The manifest section appends here as a fourth part (D-12).
  - `to_llm_messages()` at **L57-61** calls `_build_system_prompt()` → manifest flows to every LLM call automatically.
  - `to_snapshot_meta()` (L104-113) copies only explicit fields → a new `skill_manifest` dataclass field with default `None` is **non-serialized by construction** (safe: `from_events`/restore path never sees it; Phase 13-03 formalizes `skill_state` + guard).
  - Session is a `@dataclass` (L38-47) — adding `skill_manifest: str | None = None` is a plain field addition.
- `session/store.py` L33-36: `JSONLSessionStore.__init__(base_dir=None)` defaults to `Path.cwd() / ".agentharness"` — the skills dir mirrors this convention (D-01).
- `requirements.txt` currently: `openai>=1.0.0, python-dotenv>=1.0.0, tiktoken>=0.7.0, mcp>=1.27,<2, graphifyy>=0.9` — append PyYAML.
- Tests: `pytest.ini` (`asyncio_mode = auto`, `testpaths = tests`); conftest has StubAgent but skills tests need only `tmp_path` fixtures (mirror `tests/test_store.py` fixture style: `tempfile.mkdtemp()` / `tmp_path`).
- Baseline: **66 tests green** before Phase 12.
- `.agentharness/` currently holds only session JSONLs (no `skills/` dir) — discovery must tolerate a missing/empty skills dir (empty manifest → section omitted, D-13).

## Risks (from PITFALLS.md, phase-relevant subset)

| Pitfall | Phase-12 impact | Mitigation |
|---------|-----------------|------------|
| P-01 manifest overflow | Cap in **characters** (D-09), not tokens; measure the manifest itself; trim + warn (D-10) | `build_manifest_text(entries, max_chars)` + unit test "never exceeds cap for N skills" |
| P-07 malformed frontmatter crash | Discovery runs in hot path (per-call via `_build_system_prompt`); one bad file must never raise | Per-skill try/except with taxonomy (`yaml.YAMLError`, `UnicodeDecodeError`, `OSError`, type errors); discovery never raises; fixture tests: broken YAML, missing name, empty file, non-UTF8, dir without SKILL.md |
| P-08 name collisions | Folder-vs-frontmatter mismatch (D-05), win32 case-insensitive (D-06), duplicate shadowing (D-04) | Frontmatter-name-wins; case-insensitive match on win32 only; first-wins over normalized-name sort; warnings name both skills |
| — description sanitization | One multi-line description corrupts the manifest block for ALL skills (P-07 sub-case) | D-14: strip `\r\n`/control chars before embedding |
| — YAML alias/entity expansion | `yaml.safe_load` does not construct arbitrary objects | Use SafeLoader only; never `yaml.load` (T-12-01) |

## Build order (dependency-aware, mirrors ROADMAP estimate of 4 plans)

1. **12-01 foundation** — `requirements.txt` + `skills/__init__.py` + `skills/models.py` (`SkillInfo`) + `skills/frontmatter.py` (`parse_skill_doc`) + tests. Zero integration risk.
2. **12-02 discovery** — `skills/discovery.py` (`parse_skill_entry` per-skill validate+skip-and-warn; `discover_skills` scan+sort+first-wins) + fixture-based tests. Depends 12-01.
3. **12-03 manifest** — `skills/manifest.py` (`build_manifest_text` + `manifest_max_chars` env read) + budget/trim/sanitize tests. Depends 12-01. **Parallel with 12-02** (no shared files).
4. **12-04 integration** — `session/models.py` `skill_manifest` field + `_build_system_prompt()` append + end-to-end test (discover→build→set→`to_llm_messages`). Depends 12-01+12-02+12-03.

## Explicitly out of scope (deferred per CONTEXT/ROADMAP)

- Wiring (`main.py`, `harness/runtime.py` construction sites) — **Phase 14**
- `read_skill` tool, path-scoped reads, bundled resources — Phases 14-17
- `allowed-tools` enforcement (tool-list filtering) — **Phase 17** (D-17)
- Non-serialized `skill_state` + persist plumbing (`Message.persist`) — **Phase 13**
- mtime-cached discovery granularity — OpenCode discretion (executor may scan per build; O(dirs), microseconds at this scale)

---
*Synthesized 2026-08-01 from `.planning/research/{ARCHITECTURE,STACK,FEATURES,PITFALLS}.md` + verified source reads*
