# Phase 12: Skills Discovery & Manifest - Context

**Gathered:** 2026-08-01
**Status:** Ready for planning

<domain>
## Phase Boundary

Users author skills as `SKILL.md` files under `.agentharness/skills/<name>/`, and the agent sees a budgeted manifest of every valid skill's `name` + `description` in the system prompt each turn. This phase covers authoring format, one-pass discovery with skip-and-warn and deterministic first-wins, and budgeted manifest assembly with truncation. It is pure domain work: a new `skills/` package with no harness integration beyond appending the manifest section in `Session._build_system_prompt()`. The `read_skill` tool, `/skill` command, TUI indicator, and allowed-tools enforcement are later phases.

</domain>

<decisions>
## Implementation Decisions

### Skill storage & format (carried forward from milestone)
- **D-01:** Skills are project-local: `.agentharness/skills/<name>/SKILL.md` — one folder per skill, co-located with session data (MILESTONE D-01/D-02).
- **D-02:** Frontmatter: `name` + `description` required; `allowed-tools` optional (MILESTONE D-03). The `description` is the routing signal — what the skill does AND when to use it.

### Discovery & validation
- **D-03:** Malformed skills (missing/invalid frontmatter, broken YAML, empty file, non-UTF8) → log warning + skip. A broken skill never breaks the harness (MILESTONE D-04).
- **D-04:** Duplicate skill names → first-wins in a deterministic sort order + warning names the shadowed skill (MILESTONE D-05).
- **D-05:** On frontmatter-name ≠ folder-name mismatch, the **frontmatter `name` is authoritative** and the manifest uses it; the folder is just a container. A mismatch logs a warning but does not skip the skill.
- **D-06:** On Windows, a mismatch that differs only by case (e.g. `MySkill` vs `myskill`) is treated as a match — no warning (NTFS is case-insensitive). Case-sensitive compare only on non-win32.
- **D-07:** `name` validation is **lenient** — any non-empty name is accepted. Kebab-case is a documented convention, not an enforcement rule.

### Manifest cap & assembly
- **D-08:** The manifest is assembled fresh each system-prompt build (rebuilt per call = free live discovery) from a deterministic scan (MILESTONE D-06).
- **D-09:** Budget is **character-based** (model-independent), default **1,500 chars**, configurable via env var (e.g. `SKILL_MANIFEST_MAX_CHARS`) (MILESTONE D-07; research P-01).
- **D-10:** When the combined manifest exceeds the budget, over-long **descriptions are truncated** — whole skills are never dropped. Truncation is **longest-first**: sort skills by name, then trim the longest descriptions down until the whole manifest fits. All skills stay listed; every truncated description is cut with an ellipsis marker and logged with a warning.

### Manifest rendering
- **D-11:** The manifest renders as a `# Available Skills` heading followed by `- <name>: <description>` bullet lines.
- **D-12:** The manifest section is **appended at the end** of the existing parts-list in `Session._build_system_prompt()` (after AGENTS.md and CWD), keeping existing system-prompt order stable.
- **D-13:** When there are no valid skills, the section is **omitted entirely** — the system prompt stays clean (no "(none)" placeholder).
- **D-14:** Descriptions are sanitized for manifest embedding (strip newlines/control characters) before assembly.

### allowed-tools frontmatter (parsing only — enforcement is Phase 17)
- **D-15:** `allowed-tools` is parsed and shape-validated in Phase 12: must be a list of non-empty strings matching tool-name shape (letters/digits/underscore).
- **D-16:** If `allowed-tools` is present but malformed, the skill is **kept** and the field is **dropped** (treated as no restriction) with a logged warning — a broken optional field never hides the skill.
- **D-17:** Validation is **shape-only** — tool names are NOT cross-checked against the registry at discovery time (unknown tool names are allowed; they may exist at runtime). Enforcement/filtering ships in Phase 17 (MILESTONE D-16).

### OpenCode's Discretion
- Exact truncation marker text (beyond an ellipsis) and warning log wording
- Exact deterministic sort key for first-wins/trim ordering (name sort is recommended)
- Manifest cache timing detail (mtime-invalidated caching is expected but the exact granularity is open)
- Environment variable name for the cap (beyond the suggested `SKILL_MANIFEST_MAX_CHARS`)
- Whether the description-quality warning (<~20 chars) is logged in this phase
- Exception taxonomy names inside the skip-and-warn path

</decisions>

<canonical_refs>
## Canonical References

**Downstream agents MUST read these before planning or implementing.**

### Milestone & requirements (authoritative scope)
- `.planning/MILESTONE-CONTEXT.md` — Decisions D-01..D-16 for the v1.1 Skills milestone; D-01..D-07 define this phase's format, discovery, and manifest contract
- `.planning/REQUIREMENTS.md` §STORE-01..STORE-05, §DISC-01..DISC-02 — The seven requirements this phase delivers (traceability: STORE-01..05 + DISC-01/02 → Phase 12)

### Research (implementation guidance)
- `.planning/research/STACK.md` — PyYAML 6.0.3 as the single new dependency; `yaml.safe_load` + delimiter splitter pattern (~20 lines, parsing delegated to SafeLoader, degrades to `({}, body)` on error)
- `.planning/research/FEATURES.md` — Manifest shape (`- name: description`), 1,536-char Claude Code cap precedent, "None when no skills"
- `.planning/research/ARCHITECTURE.md` — `skills/` package layout (`models.py`, `frontmatter.py`, `discovery.py`, `manifest.py`), one-way deps (never imports `agent/`), manifest injection at `_build_system_prompt()`
- `.planning/research/PITFALLS.md` — P-01 (enforce cap in characters, measure whole prompt), P-07 (per-skill try/except taxonomy, fixture tests: broken YAML, missing name, empty file, non-UTF8, dir without SKILL.md), P-08 (name collisions incl. folder-vs-frontmatter + win32 case)

### Codebase integration points
- `session/models.py` §`_build_system_prompt` (lines 63-69) — parts-list assembler; the manifest section appends here (D-12)
- `requirements.txt` — add `PyYAML>=6.0.3`
- `llm/base.py` §`count_tokens` (line 49) — tiktoken counting; available for accounting but the cap unit is characters (D-09)

### Authoring format references
- `.opencode/skills/graphify/SKILL.md` — Existing frontmatter `name`/`description` + body format the milestone was modeled on
- https://agentskills.io/specification — Open Agent Skills standard: name/description requirements, progressive disclosure (external)

</canonical_refs>

<code_context>
## Existing Code Insights

### Reusable Assets
- `Session._build_system_prompt()` (`session/models.py:63-69`): existing parts-list system-prompt assembler — the manifest section appends to this list (D-12). It is rebuilt per `to_llm_messages()` call, so per-call manifest rebuild comes free.
- `Message`/`ConversationContext` (`context/`): not used this phase (injection is Phase 14), but the system-role summarization exemption (`context/context.py:88`) is why bodies can be exempt later — worth documenting in the plan.
- Existing skill files (`.opencode/skills/graphify/SKILL.md`) and reference examples (`.agents/skills/grilling/SKILL.md`) — real-world frontmatter for fixture tests.

### Established Patterns
- Dataclass models + explicit `__all__` barrel exports per package (`__init__.py`), absolute imports from project root (CONVENTIONS.md)
- Skip-and-warn error handling: corrupt data logged + skipped, never crashes the harness (matches `session/store.py` corrupt-JSONL handling)
- Module-level `logger = logging.getLogger(__name__)`; warnings at `logger.warning()`
- `asyncio.to_thread` for blocking I/O (not needed for discovery at this scale — `os.scandir`/`Path.iterdir()` is synchronous and fast)

### Integration Points
- `session/models.py` `_build_system_prompt()` — append the `# Available Skills` section (D-11/D-12); `to_llm_messages()` calls it, so the manifest flows to every LLM call automatically
- New `skills/` package: `models.py` (SkillInfo dataclass: name, description, allowed-tools, path), `frontmatter.py` (delimiter splitter + `yaml.safe_load`), `discovery.py` (one-pass scan, skip-and-warn, first-wins), `manifest.py` (budgeted assembly + longest-first truncation)
- Wiring lives in `main.py` / `harness/runtime.py` (Phase 14 concern) — Phase 12 delivers the package + the `_build_system_prompt()` integration + tests

</code_context>

<specifics>
## Specific Ideas

- "I need it for my .agentharness (required)" — skills are project-local, live under the existing `.agentharness/` data dir (D-01)
- "skill similar like claude codes skill with progressive disclosure" — the load model should be: manifest in system prompt (cheap), body on tool-call (when relevant); this phase delivers the manifest half
- Modeled directly on Claude Code Agent Skills / agentskills.io — manifest shape, ~1,500-char cap, skip-and-warn all mirror the reference implementation
- User chose frontmatter-name-wins and lenient name validation — authoring stays forgiving; broken skills degrade to warnings, never errors

</specifics>

<deferred>
## Deferred Ideas

- `read_skill` tool, `/skill` command, TUI "Skill loaded" indicator — Phases 14-16
- allowed-tools enforcement (tool-list filtering) — Phase 17
- Manifest rebuild timing / frontmatter caching decisions — OpenCode discretion, folded into this phase's implementation
- Description-quality warning threshold (<~20 chars) — optional nicety, OpenCode discretion
- Skill authoring/management tools, `/skills` listing, script-as-tool, user-global dir, marketplace — future milestone (see MILESTONE-CONTEXT deferred)
- None — discussion stayed within phase scope

</deferred>

---

*Phase: 12-skills-discovery-manifest*
*Context gathered: 2026-08-01*
