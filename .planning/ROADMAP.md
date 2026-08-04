# AgentHarness Roadmap

**Updated:** 2026-08-04

## Milestones

- ✅ **v1.0 AgentHarness MVP** — Phases 1-11 (shipped 2026-08-01)
- ✅ **v1.1 Skills System** — Phases 12-17 (shipped 2026-08-04; Phase 17 cancelled — CAP-02/CAP-04 deferred)

## Phases

**Phase Numbering:**
- Integer phases (1, 2, 3): Planned milestone work
- Decimal phases (2.1, 2.2): Urgent insertions (marked with INSERTED)

Decimal phases appear between their surrounding integers in numeric order.
Phase numbering continues across milestones (never restarts at 01).

<details>
<summary>✅ v1.1 Skills System (Phases 12-17) — SHIPPED 2026-08-04</summary>

- [x] Phase 12: Skills Discovery & Manifest (4/4 plans) — completed 2026-08-01
- [x] Phase 13: Context Plumbing (Persist Fix) (3/3 plans) — completed 2026-08-01
- [x] Phase 14: read_skill Provider End-to-End (5/5 plans) — completed 2026-08-02
- [x] Phase 15: Session Behavior & /skill Command (3/3 plans) — completed 2026-08-02
- [x] Phase 16: TUI Integration (Skill Indicator) (5/5 plans) — completed 2026-08-04
- [ ] Phase 17: allowed-tools Enforcement & Hardening (0/3 plans) — CANCELLED 2026-08-04 (CAP-02/CAP-04 deferred to future/end milestone)

**Milestone summary:** Progressive-disclosure skills — `SKILL.md` files under `.agentharness/skills/`, budgeted manifest in the system prompt, on-demand body loading via `read_skill` and `/skill`, session-scoped non-persisted system-role bodies, TUI skill indicator. Full details: `.planning/milestones/v1.1-ROADMAP.md`.

</details>

<details>
<summary>✅ v1.0 AgentHarness MVP (Phases 1-11) — SHIPPED 2026-08-01</summary>

- [x] Phase 1: Core Harness — completed 2026-08-01
- [x] Phase 2: Session Module — completed 2026-08-01
- [x] Phase 3: Fix Summarization — completed 2026-08-01
- [x] Phase 4: Textual TUI + Queue + Worker — completed 2026-08-01
- [x] Phase 5: Harness Runtime (8/8 plans) — completed 2026-08-01
- [x] Phase 6: Rich Textual TUI (3/3 plans) — completed 2026-08-01
- [x] Phase 7: TUI Visual Overhaul (3/3 plans) — completed 2026-08-01
- [x] Phase 8: TUI Conversation Layout (3/3 plans) — completed 2026-08-01
- [x] Phase 9: TS TUI JSON-RPC (4/4 plans) — completed 2026-08-01
- [x] Phase 10: Token Streaming (4/4 plans) — completed 2026-07-31
- [x] Phase 11: Session Popup & Panel Layout (4/4 plans) — completed 2026-08-01

**Milestone summary:** Core LLM ↔ tool loop, session persistence (JSONL), Textual TUI → Ink/React TUI over JSON-RPC stdio, harness RuntimeAPI, token streaming, conversation-first layout. Full details: `.planning/milestones/v1.0-ROADMAP.md`.

</details>

### 📋 Next Milestone (Planned)

Requirements for the next milestone (v1.2 and beyond) are re-defined via `/gsd-new-milestone`.

### Future (backlog)

- Tool system hardening (remove_provider, health-check, reconnect)
- Multi-turn agent improvements
- Package restructuring
- v1.2 Skills: authoring/management UI, `/skills` listing, script-as-tool, user-global skills dir, skill chaining
- allowed-tools enforcement (CAP-02/CAP-04) — deferred from v1.1 Phase 17; pure contracts (`retain_read_skills`, `intersect_allowed_tools`) already shipped in `skills/filter.py`

## Progress

| Phase | Milestone | Plans Complete | Status | Completed |
|-------|-----------|----------------|--------|-----------|
| 1. Core Harness | v1.0 | - | Complete | 2026-08-01 |
| 2. Session Module | v1.0 | - | Complete | 2026-08-01 |
| 3. Fix Summarization | v1.0 | - | Complete | 2026-08-01 |
| 4. Textual TUI + Queue + Worker | v1.0 | - | Complete | 2026-08-01 |
| 5. Harness Runtime | v1.0 | 8/8 | Complete | 2026-08-01 |
| 6. Rich Textual TUI | v1.0 | 3/3 | Complete | 2026-08-01 |
| 7. TUI Visual Overhaul | v1.0 | 3/3 | Complete | 2026-08-01 |
| 8. TUI Conversation Layout | v1.0 | 3/3 | Complete | 2026-08-01 |
| 9. TS TUI JSON-RPC | v1.0 | 4/4 | Complete | 2026-08-01 |
| 10. Token Streaming | v1.0 | 4/4 | Complete | 2026-07-31 |
| 11. Session Popup & Panel Layout | v1.0 | 4/4 | Complete | 2026-08-01 |
| 12. Skills Discovery & Manifest | v1.1 | 4/4 | Complete | 2026-08-01 |
| 13. Context Plumbing (Persist Fix) | v1.1 | 3/3 | Complete | 2026-08-01 |
| 14. read_skill Provider End-to-End | v1.1 | 5/5 | Complete | 2026-08-02 |
| 15. Session Behavior & /skill Command | v1.1 | 3/3 | Complete | 2026-08-02 |
| 16. TUI Integration (Skill Indicator) | v1.1 | 5/5 | Complete | 2026-08-04 |
| 17. allowed-tools Enforcement & Hardening | v1.1 | 0/3 | Cancelled | 2026-08-04 |
