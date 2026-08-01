# Requirements: AgentHarness

**Defined:** 2026-08-01
**Core Value:** A reliable, session-persistent terminal chat loop where the LLM agent drives tools — with a TUI that makes long conversations fast to navigate and continue.

## v1.1 Requirements (Skills System)

### Skill Storage & Format

- [ ] **STORE-01**: User can author a skill as a `SKILL.md` file at `.agentharness/skills/<name>/SKILL.md` (one folder per skill)
- [ ] **STORE-02**: Skill name is kebab-case and matches the folder name
- [ ] **STORE-03**: User can provide `name` and `description` frontmatter (required) and `allowed-tools` (optional)
- [ ] **STORE-04**: Skills with missing/invalid frontmatter are skipped with a warning and never break the harness
- [ ] **STORE-05**: Duplicate skill names resolve deterministically (first-wins) with a warning about the shadowed skill

### Progressive Disclosure

- [ ] **DISC-01**: Agent sees a manifest of every skill's `name` + `description` in the system prompt each turn
- [ ] **DISC-02**: Manifest is subject to a budget (character/token cap) with trimming of over-long skills
- [ ] **DISC-03**: Agent can load a skill body on demand via a dedicated `read_skill` tool when the description matches the current task
- [ ] **DISC-04**: `read_skill` reads are path-scoped to the skills directory — no traversal outside it
- [ ] **DISC-05**: Skills support bundled resources (`references/`, `scripts/`, `assets/`) readable on demand through path-scoped reads into the skill directory

### Activation & Session Behavior

- [ ] **ACT-01**: User can force-load a skill via a `/skill <name>` slash command
- [ ] **ACT-02**: Agent auto-invokes skills when a manifest description matches the current task
- [ ] **ACT-03**: Loaded skill body persists for the rest of the session as a system-role message
- [ ] **ACT-04**: Loaded skill bodies survive context summarization (system-role exemption)
- [ ] **ACT-05**: Loaded skills are session-scoped — never persisted to the JSONL session file
- [ ] **ACT-06**: TUI shows a visible indicator when a skill is loaded

### Skill Capabilities

- [ ] **CAP-01**: Skill bodies are markdown instructions that can reference bundled files relative to the skill directory
- [ ] **CAP-02**: A skill's optional `allowed-tools` filters the tool list passed to the LLM while the skill is loaded
- [ ] **CAP-03**: `read_skill` is always retained in the tool list even when `allowed-tools` filtering is active
- [ ] **CAP-04**: When multiple skills with `allowed-tools` are loaded, filtering uses documented intersection semantics

## v1.2 Requirements (Future)

### Skill Authoring & Management

- **AUTH-01**: User can create, list, and edit skills from the harness (management tools)
- **AUTH-02**: TUI shows a `/skills` listing command

### Expanded Skills

- **EXPD-01**: Skills bundle scripts that register as first-class harness tools (script-as-tool)
- **EXPD-02**: Skills live in a user-global directory (~/.config/agentharness/skills/) for cross-project reuse
- **EXPD-03**: Skill chaining / nested skills
- **EXPD-04**: Skill marketplace / sharing / plugin-provided skills

## Out of Scope

| Feature | Reason |
|---------|--------|
| Keyword/algorithmic skill matching | Progressive disclosure uses pure LLM reasoning over descriptions (D-06, ecosystem standard) |
| Script-as-tool registration | D-15 defers — skills are markdown instructions + bundled files in v1.1 |
| Persisting loaded skill bodies to JSONL | D-13 — loaded skills are session-scoped |
| Loading all skill bodies at startup | Defeats progressive disclosure entirely |
| Skill authoring UI / management tools | Deferred to v1.2 |
| User-global skills directory | Deferred to v1.2 (D-01: project-local only) |
| Manifest with no cap | Unbounded system-prompt growth as skills accumulate |

## Traceability

Which phases cover which requirements. Updated during roadmap creation.

| Requirement | Phase | Status |
|-------------|-------|--------|
| STORE-01 | Phase 12 | Pending |
| STORE-02 | Phase 12 | Pending |
| STORE-03 | Phase 12 | Pending |
| STORE-04 | Phase 12 | Pending |
| STORE-05 | Phase 12 | Pending |
| DISC-01 | Phase 12 | Pending |
| DISC-02 | Phase 12 | Pending |
| DISC-03 | Phase 14 | Pending |
| DISC-04 | Phase 14 | Pending |
| DISC-05 | Phase 14 | Pending |
| ACT-01 | Phase 15 | Pending |
| ACT-02 | Phase 14 | Pending |
| ACT-03 | Phase 13 | Pending |
| ACT-04 | Phase 13 | Pending |
| ACT-05 | Phase 13 | Pending |
| ACT-06 | Phase 16 | Pending |
| CAP-01 | Phase 14 | Pending |
| CAP-02 | Phase 17 | Pending |
| CAP-03 | Phase 14 | Pending |
| CAP-04 | Phase 17 | Pending |

**Coverage:**
- v1.1 requirements: 20 total
- Mapped to phases: 20
- Unmapped: 0 ✓

**Mapping rationale:**
- **Phase 12 (Skills Discovery & Manifest):** STORE-01..05 + DISC-01..02 — pure domain: authoring format, skip-and-warn discovery, budgeted manifest.
- **Phase 13 (Context Plumbing / Persist Fix):** ACT-03..05 — the persist flag + `mark_saved()` index fix makes bodies persist in-session (system-role, summarization-exempt) but never to JSONL. Placed second so the D-13 leak is closed before any real body flows.
- **Phase 14 (read_skill Provider End-to-End):** DISC-03..05, ACT-02, CAP-01, CAP-03 — the tool, path-scoped reads, bundled resources, and the never-filtered retention contract ship together.
- **Phase 15 (Session Behavior & /skill Command):** ACT-01 — `/skill` via the 4-layer RPC contract + REPL; combined-filter semantics decision locked here (CAP-04 design-before-implementation).
- **Phase 16 (TUI Integration):** ACT-06 — typed `skill_loaded` notification + visible indicator + TUI `/skill` intercept.
- **Phase 17 (allowed-tools Enforcement & Hardening):** CAP-02, CAP-04 — per-iteration filter projection, intersection semantics, E2E verification.

---
*Requirements defined: 2026-08-01*
*Last updated: 2026-08-01 after roadmap creation (v1.1, phases 12-17)*
