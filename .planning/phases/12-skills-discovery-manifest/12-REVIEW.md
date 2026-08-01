---
phase: 12-skills-discovery-manifest
reviewed: 2026-08-01T00:00:00Z
depth: standard
files_reviewed: 11
files_reviewed_list:
  - requirements.txt
  - skills/__init__.py
  - skills/models.py
  - skills/frontmatter.py
  - skills/discovery.py
  - skills/manifest.py
  - session/models.py
  - tests/test_skills_frontmatter.py
  - tests/test_skills_discovery.py
  - tests/test_skills_manifest.py
  - tests/test_skills_integration.py
findings:
  critical: 0
  warning: 4
  info: 4
  total: 8
status: issues_found
---

# Phase 12: Code Review Report

**Reviewed:** 2026-08-01T00:00:00Z
**Depth:** standard
**Files Reviewed:** 11
**Status:** issues_found

## Summary

Reviewed the skills discovery/manifest subsystem (frontmatter parsing, directory
discovery, D-09..D-16 manifest budgeting) plus the `Session` integration surface in
`session/models.py`. All 37 tests pass and all imports resolve. The core logic is
well-factored and the D-06/D-10/D-14 contracts are mostly honored, but four warnings
were found: the manifest's newline-sanitization (D-14) protects *descriptions* but
not *names* — a skill name containing a newline corrupts the entire manifest block
(confirmed empirically); SKILL.md files saved with a UTF-8 BOM are silently skipped;
`_build_system_prompt` reads AGENTS.md with the locale encoding (cp1252 on win32),
which crashes on non-Latin1 content; and `unpersisted_events()` reproduces the exact
AttributeError bug class that `get_messages()` was written to avoid. All findings were
reproduced with probes against the actual code, not just static reading.

## Warnings

### WR-01: Skill names bypass the D-14 sanitization contract — manifest corruption

**File:** `skills/discovery.py:56` (and `skills/manifest.py:42`)
**Issue:** D-14 sanitizes `description` so "one bad description can't corrupt the
manifest block for every other skill", but `name` is only `.strip()`ed in
`parse_skill_entry` and rendered raw in `_render()` (`f"- {s.name}: {descs[s.name]}"`).
A frontmatter name containing a newline/CR/tab — trivially writable via a YAML block
scalar or an escaped `\n` — injects raw lines into the system prompt. Confirmed:
`name: |` with two lines renders `'# Available Skills\n- line1\nline2\n: x'`, breaking
the list structure for every skill and violating the phase's own D-14 embedding
contract. `parse_skill_entry` accepts any non-empty string (D-07) with no
control-character check.
**Fix:** Sanitize names with the same character policy as D-14, either at validation
in `parse_skill_entry` (preferred — also protects callers that bypass discovery) or in
`build_manifest_text`:
```python
# skills/manifest.py — apply to names in _render, or in discovery before SkillInfo()
def _sanitize_name(name: str) -> str:
    replaced = name.replace("\r", " ").replace("\n", " ").replace("\t", " ")
    cleaned = "".join(ch for ch in replaced if ord(ch) >= 32 and ord(ch) != 127)
    return " ".join(cleaned.split())
```
D-07 can stay lenient ("any non-empty name"), but the *rendered* name must be a single
line.

### WR-02: UTF-8 BOM in SKILL.md silently drops valid skills

**File:** `skills/discovery.py:46`
**Issue:** `skill_file.read_text(encoding="utf-8")` leaves a `\ufeff` BOM in the first
line, so `parse_skill_doc`'s `text.startswith("---")` fails, the frontmatter is never
parsed, and the skill is skipped with "missing or invalid frontmatter 'name'". BOMs are
common on Windows (Notepad/VS Code default), and this project targets win32.
Confirmed: a SKILL.md written as `b"\xef\xbb\xbf---\nname: bomskill\n..."` returns
`None` from `parse_skill_entry`.
**Fix:** `skill_file.read_text(encoding="utf-8-sig")` — the `utf-8-sig` codec strips a
leading BOM when present and is byte-identical to `utf-8` otherwise.

### WR-03: `_build_system_prompt` reads AGENTS.md with the locale encoding — crashes on non-Latin1 content

**File:** `session/models.py:68`
**Issue:** `agents_md.read_text()` uses `locale.getpreferredencoding(False)`, which is
**cp1252** on this win32 machine (Python 3.12.5). Any UTF-8 AGENTS.md containing bytes
undefined in cp1252 (CJK, emoji, etc.) raises `UnicodeDecodeError`, crashing
`to_llm_messages()` — the core path of every conversation turn. Confirmed with a file
containing byte `0x81`: `RAISES: UnicodeDecodeError 'charmap' codec can't decode byte
0x81`. Note the skills subsystem reads files with explicit `utf-8`; this site is
inconsistent with it.
**Fix:**
```python
agents_md = Path("AGENTS.md")
if agents_md.exists():
    parts.append(f"# Project Instructions\n\n{agents_md.read_text(encoding='utf-8-sig')}")
```

### WR-04: `unpersisted_events()` reintroduces the AttributeError bug class that `get_messages()` exists to avoid

**File:** `session/models.py:100-102`
**Issue:** On a store-loaded session (`from_events`, `_context is None`), `to_events()`
dereferences `self._context._messages` → `AttributeError: 'NoneType' object has no
attribute '_messages'` (confirmed). `get_messages()` (lines 88-98) explicitly guards
this exact failure and its docstring calls it "empirically confirmed" — but
`unpersisted_events()` calls `to_events()` unconditionally, while its sibling
`mark_saved()` is a silent no-op on the same session. Any code calling
`unpersisted_events()` before `restore_context()` crashes instead of degrading.
**Fix:** Mirror the `get_messages()` guard:
```python
def unpersisted_events(self) -> list[dict]:
    if self._context is None:
        return [dict(e) for e in getattr(self, "_stored_events", [])][self._last_saved_count:]
    return self.to_events()[self._last_saved_count:]
```

## Info

### IN-01: Frontmatter delimiter scan ends early on column-0 `---` inside a block scalar

**File:** `skills/frontmatter.py:17-20`
**Issue:** The closing-delimiter scan matches any line whose stripped content is
`---`, including a block-scalar line at column 0 (e.g. `description: |2`). Confirmed:
`"---\nname: foo\ndescription: |2\n---\n  two\n---\n\nreal"` parses to
`meta == {'name': 'foo', 'description': ''}` and `body == '  two\n---\n\nreal'` — the
real delimiter is swallowed into the body and the description is lost, so the skill is
silently skipped downstream. Rare (requires an explicit indentation indicator), but a
naive line-scan frontmatter splitter is the root cause.
**Fix:** If block scalars in frontmatter are a real concern, either reject/lint
frontmatter containing column-0 `---` within a `|`/`>` scalar, or track YAML block
scalar state during the scan. At minimum, add a test documenting the behavior.

### IN-02: `build_manifest_text` keyed by name — duplicate names silently collapse

**File:** `skills/manifest.py:42,63`
**Issue:** `descs = {s.name: ...}` and `_render` look up by name, so passing two
entries with the same name renders both lines with the *second* description
(confirmed: `'- dup: second\n- dup: second'`). `discover_skills` dedupes, but
`build_manifest_text` is a public API taking an arbitrary `Sequence[SkillInfo]`.
Related cosmetic issue: names starting with `- ` render as `- - starts with dash: x`.
**Fix:** Key `descs` by identity/index (`descs[i]` parallel to `ordered`) or reject
duplicate names; optionally strip a leading `-` from names before rendering.

### IN-03: AGENTS.md resolved relative to CWD, silently omitted when launched elsewhere

**File:** `session/models.py:66-68`
**Issue:** `Path("AGENTS.md")` and `os.getcwd()` depend on the process working
directory. The integration tests pass because pytest's CWD is the project root; a
shortcut/agent launching the app from another directory silently loses project
instructions and gets a wrong `# Environment` CWD line.
**Fix:** Anchor AGENTS.md to a project root resolved once at startup (e.g.
`Path(__file__).resolve().parents[1] / "AGENTS.md"`) rather than the transient CWD.

### IN-04: `graphifyy>=0.9` in requirements.txt — likely a package-name typo

**File:** `requirements.txt:5`
**Issue:** The repo (AGENTS.md, the graphify skill) references the `graphify` tool,
but the pinned dependency is `graphifyy` (double y). If the correct PyPI package is
`graphify`, this line would install an unrelated/lookalike package. Verify the correct
package name before shipping.
**Fix:** Confirm the intended package and dependency name with the author; correct the
line if it is a typo.

---

_Reviewed: 2026-08-01T00:00:00Z_
_Reviewer: OpenCode (gsd-code-reviewer)_
_Depth: standard_
