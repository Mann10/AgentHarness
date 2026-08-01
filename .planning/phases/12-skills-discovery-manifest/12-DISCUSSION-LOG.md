# Phase 12: Skills Discovery & Manifest - Discussion Log

> **Audit trail only.** Do not use as input to planning, research, or execution agents.
> Decisions are captured in CONTEXT.md — this log preserves the alternatives considered.

**Date:** 2026-08-01
**Phase:** 12-skills-discovery-manifest
**Areas discussed:** Manifest cap behavior, Name mismatch policy, Manifest rendering, allowed-tools parsing

---

## Manifest cap behavior

| Option | Description | Selected |
|--------|-------------|----------|
| Truncate descriptions | Each over-long description deterministically truncated (first N chars + "…"); all skills stay listed | ✓ |
| Drop whole skills | Skills sorted deterministically, whole skills dropped until total fits | |
| Truncate then drop | Per-skill max truncation, then drop only if total still exceeds | |

**User's choice:** Truncate descriptions
**Notes:** All skills remain visible; D-07 "skills over the cap are trimmed" interpreted as truncation, not dropping.

---

## Manifest cap behavior (follow-up: truncation mechanics)

| Option | Description | Selected |
|--------|-------------|----------|
| Longest-first trim | Sort by name, truncate longest descriptions down until whole manifest fits | ✓ |
| Fixed per-skill ceiling | Truncate each over-long description to fixed ceiling regardless of total | |
| Per-skill cap only | Only cap each individual description; total cap advisory | |

**User's choice:** Longest-first trim
**Notes:** Deterministic ordering; over-long descriptions cut with ellipsis + logged warning.

---

## Manifest cap behavior (follow-up: budget constant)

| Option | Description | Selected |
|--------|-------------|----------|
| 1500, configurable | ~1,500 chars Claude Code precedent, env-configurable with 1500 default | ✓ |
| 800, configurable | Tighter budget, more truncation risk | |
| 3000, configurable | More headroom, higher per-turn prompt cost | |

**User's choice:** 1500, configurable

---

## Name mismatch policy

| Option | Description | Selected |
|--------|-------------|----------|
| Frontmatter wins | Frontmatter `name` authoritative; warn on mismatch but use it | ✓ |
| Folder wins | Folder name authoritative (D-02); warn but resolve to folder | |
| Skip the skill | Mismatch = malformed → skip-and-warn | |

**User's choice:** Frontmatter wins
**Notes:** Folder is just a container; the manifest uses the frontmatter name.

---

## Name mismatch policy (follow-up: case rules)

| Option | Description | Selected |
|--------|-------------|----------|
| Case-insensitive match | On win32, case-only differences treated as matching, no warning | ✓ |
| Case-sensitive always | Strict compare everywhere; case-only mismatch warns | |

**User's choice:** Case-insensitive match

---

## Name mismatch policy (follow-up: kebab-case enforcement)

| Option | Description | Selected |
|--------|-------------|----------|
| Enforce kebab-case | Validate name is lowercase/hyphen/no-space; warn + skip if not | |
| Lenient | Accept any non-empty name; kebab-case is convention only | ✓ |

**User's choice:** Lenient

---

## Manifest rendering

| Option | Description | Selected |
|--------|-------------|----------|
| Heading + bullets | `# Available Skills` heading + `- <name>: <description>` lines | ✓ |
| Bullets only | No heading, inline bullet list | |

**User's choice:** Heading + bullets

---

## Manifest rendering (follow-up: placement)

| Option | Description | Selected |
|--------|-------------|----------|
| Append at end | Append after AGENTS.md and CWD; existing order stable | ✓ |
| Early (before AGENTS.md) | Insert after base system_prompt, before AGENTS.md | |

**User's choice:** Append at end

---

## Manifest rendering (follow-up: empty state)

| Option | Description | Selected |
|--------|-------------|----------|
| Omit section | No valid skills → no section at all | ✓ |
| Always render | Heading always present, e.g. "(none)" | |

**User's choice:** Omit section

---

## Manifest rendering (follow-up: line format)

| Option | Description | Selected |
|--------|-------------|----------|
| name: description | `- <name>: <description>` one line per skill | ✓ |
| Two-line entries | Name line + indented description line | |

**User's choice:** name: description

---

## allowed-tools parsing

| Option | Description | Selected |
|--------|-------------|----------|
| Parse + validate now | Parse/validate in Phase 12; enforcement in Phase 17 | ✓ |
| Defer to Phase 17 | Ignore in Phase 12; enter model at enforcement | |

**User's choice:** Parse + validate now
**Notes:** STORE-03 includes allowed-tools; malformed value validated early so Phase 17 only implements.

---

## allowed-tools parsing (follow-up: malformed handling)

| Option | Description | Selected |
|--------|-------------|----------|
| Keep skill, drop field | Keep skill, log warning, treat as no restriction | ✓ |
| Skip whole skill | Malformed allowed-tools → whole skill malformed → skip | |

**User's choice:** Keep skill, drop field

---

## allowed-tools parsing (follow-up: tool-name validation)

| Option | Description | Selected |
|--------|-------------|----------|
| Shape-only validation | Non-empty strings with tool-name shape; unknown names allowed | ✓ |
| Cross-check registry | Verify each tool exists in registry at discovery | |

**User's choice:** Shape-only validation

---

## OpenCode's Discretion

- Exact truncation marker text and warning wording
- Exact deterministic sort key for first-wins/trim
- Manifest cache timing detail (mtime-invalidation granularity)
- Env var name for the cap
- Description-quality warning threshold
- Exception taxonomy names

## Deferred Ideas

- read_skill / /skill / TUI indicator / enforcement — Phases 14-17
- Manifest caching, description-quality warnings — folded into implementation (OpenCode discretion)
- Authoring tools, /skills, script-as-tool, user-global, marketplace — future milestone
