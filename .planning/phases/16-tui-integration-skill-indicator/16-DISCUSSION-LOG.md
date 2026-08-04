# Phase 16: TUI Integration (Skill Indicator) - Discussion Log

> **Audit trail only.** Do not use as input to planning, research, or execution agents.
> Decisions are captured in CONTEXT.md — this log preserves the alternatives considered.

**Date:** 2026-08-03
**Phase:** 16-tui-integration-skill-indicator
**Areas discussed:** Indicator form & placement, Multiple loaded skills, /skill TUI feedback, Notification contract (payload), Restore / session-switch sync

---

## Indicator form & placement

| Option | Description | Selected |
|--------|-------------|----------|
| Footer chip, persistent | Live chip in the footer (e.g. `⚡ demo-greeter`) that stays visible for the whole session and clears on /new | ✓ |
| Inline notice, transient | Notice in the conversation stream ('Skill loaded: demo-greeter') that scrolls away like 'Cancelled' | |
| Both | Persistent footer chip AND transient inline notice on load | |

**User's choice:** Footer chip, persistent
**Notes:** Matches roadmap's "footer chip" wording and the session-persistent reality of loaded skills.

| Option | Description | Selected |
|--------|-------------|----------|
| Dedicated line above hints | Chip line above the existing hint row (e.g. `Skill: demo-greeter · weather`) | ✓ |
| Inline on hint row | Append chip inline on the existing hint row | |
| You decide | Leave exact placement to the planner | |

**User's choice:** Dedicated line above hints
**Notes:** Hints stay; chip line appears/disappears with loaded skills.

---

## Multiple loaded skills

| Option | Description | Selected |
|--------|-------------|----------|
| All loaded skills | Chip shows all loaded skill names | ✓ |
| Most recent only | Chip shows only the most recently loaded skill | |

**User's choice:** All loaded skills
**Notes:** Transparency — every loaded body stays in context for the session and Phase 17 combines loaded skills' allowed-tools via intersection.

---

## /skill TUI feedback

| Option | Description | Selected |
|--------|-------------|----------|
| Notices for every outcome | Inline notice mirrors REPL ack wording for loaded / already_loaded / not_found | ✓ |
| Silent on success | Notice only for errors; chip is the only success feedback | |
| Chip-only, no notices | Footer chip is the only feedback, errors via existing error state | |

**User's choice:** Notices for every outcome
**Notes:** Mirrors Phase 15's distinct error/usage contract, in the TUI.

| Option | Description | Selected |
|--------|-------------|----------|
| Show usage notice | Bare `/skill` shows `Usage: /skill <name>` and never forwards to chat | ✓ |
| Send as chat prompt | Bare `/skill` falls through to a normal chat prompt | |

**User's choice:** Show usage notice
**Notes:** Same no-fall-through rule as the REPL (15-CONTEXT D-02).

---

## Notification contract (payload)

| Option | Description | Selected |
|--------|-------------|----------|
| Name only | Notification carries `{ skill: <canonical name> }`; status lives in the skills.load RPC response | ✓ |
| Name + status | Notification carries `{ skill, status: loaded }` too — redundant since event fires only on real loads | |

**User's choice:** Name only
**Notes:** Lean payload, one source of truth per concern. Event fires from shared `load_skill()` path so both read_skill and /skill trigger it; already_loaded emits nothing.

---

## Restore / session-switch sync

| Option | Description | Selected |
|--------|-------------|----------|
| Live events only | Chip reflects only skill_loaded notifications seen by this TUI instance; clears on /new and session switch | ✓ |
| Sync skill_state on switch | Expose backend skill_state over RPC to re-populate the chip across switches | |

**User's choice:** Live events only
**Notes:** No new RPC surface. ACT-06 only requires an indicator "whenever a skill loads".

---

## OpenCode's Discretion

- Exact chip styling (colors, separator/icon, truncation when many skills) and footer layout details
- `SkillLoadedEvent` dataclass field names and exact payload-extractor implementation in `server.py`
- Exact usage-line wording and notice styling
- Whether the notice reuses `addNotice` or a dedicated variant
- `loadedSkills` zustand store shape and reset semantics

## Deferred Ideas

- Backend `skill_state` sync over RPC (rejected in D-09) — scope expansion beyond ACT-06
- `/skills` listing command (AUTH-02, v1.2) — already deferred from Phase 15
- Skill indicator in the tool-monitor panel — footer chip is the chosen home
- Skill unload / removal UX — skills cleared only by `/new`

---

*Phase: 16-tui-integration-skill-indicator*
*Discussion log generated: 2026-08-03*
