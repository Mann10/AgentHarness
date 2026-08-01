# AgentHarness Roadmap

**Updated:** 2026-08-01

## Milestones

- ✅ **v1.0 AgentHarness MVP** — Phases 1-11 (shipped 2026-08-01)
- 🚧 **v1.1 Skills System** — Phases 12-17 (in progress)

## Phases

**Phase Numbering:**
- Integer phases (1, 2, 3): Planned milestone work
- Decimal phases (2.1, 2.2): Urgent insertions (marked with INSERTED)

Decimal phases appear between their surrounding integers in numeric order.
v1.1 continues v1.0's numbering: it starts at Phase 12.

<details>
<summary>✅ v1.0 AgentHarness MVP (Phases 1-11) — SHIPPED 2026-08-01</summary>

### Phase 1: Core Harness ✓

**Goal:** Build the core LLM ↔ tool interaction loop with OpenAI-compatible client, tool registry, and REPL interface.

**Deliverables:** `main.py`, `agent/core.py`, `llm/`, `tool/registry.py`, `tool/local_provider.py`, `tool/mcp_provider.py`, `config.py`

---

### Phase 2: Session Module ✓

**Goal:** Add session persistence and management — create, resume, list, and switch conversations.

**Deliverables:** `session/models.py`, `session/store.py`, `/sessions`, `/new`, `/resume`, `/title` commands in REPL

---

### Phase 3: Fix Summarization

**Goal:** Fix the broken conversation summarization system — resolve `NameError` crash, O(n²) performance bug, and `LLMResponse`→`str` type mismatch. Improve the summarization prompt structure.

**Key decisions:** Summarize all messages at threshold, keep `_keep_recent_exchanges` (default: 1), soft degrade on failure.

---

### Phase 4: Textual TUI + Queue + Worker ✓

**Goal:** Replace the raw `input()` REPL with a Textual TUI. Add a durable async job queue (SQLite-backed asyncio.Queue), a `--worker` mode for background processing, and a `--tui` flag for the new Textual interface.

**Deliverables:** `queue/models.py`, `queue/store.py`, `queue/manager.py`, `tui/app.py`, `tui/widgets/`, `tui/screens/`, `main.py --tui`, `main.py --worker`

---

### Phase 5: Harness Runtime

**Goal:** Create a Harness Runtime layer between the TUI and Agent that owns request lifecycle, event distribution, session management, and background scheduling.

**Deliverables:** `harness/events.py`, `harness/event_bus.py`, `harness/scheduler.py`, `harness/session_manager.py`, `harness/cancellation.py`, `harness/runtime.py`, `harness/__init__.py`, `tests/conftest.py`, `tests/test_session_manager.py`, `tests/test_agent_events.py`, `tests/test_scheduler.py`, `tests/test_runtime.py`, `pytest.ini`

**Plans:** 8 plans in 5 waves — Complete

Plans:
- [x] 05-00-PLAN.md — Test infrastructure (pytest.ini, conftest.py)
- [x] 05-01-PLAN.md — EventBus + Events + Cancellation
- [x] 05-02-PLAN.md — SessionManager
- [x] 05-03-PLAN.md — Agent event emission hooks
- [x] 05-04-PLAN.md — Scheduler (one-turn dispatch + backlog)
- [x] 05-05-PLAN.md — RuntimeAPI + harness/__init__.py
- [x] 05-06-PLAN.md — TUI refactor to pure view layer
- [x] 05-07-PLAN.md — main.py Runtime wiring

---

### Phase 6: Rich Textual TUI

**Goal:** Transform the minimal Textual TUI into a professional-grade terminal interface with rich components — conversation view with Markdown rendering, inline collapsible tool call cards, job queue sidebar, tool call timeline, session picker modal, and enhanced status/input bars. All widgets driven by the existing EventBus.

**Deliverables:** `tui/widgets/conversation_view.py`, `tui/widgets/message_card.py`, `tui/widgets/tool_call_card.py`, `tui/widgets/job_queue_sidebar.py`, `tui/widgets/tool_timeline.py`, `tui/screens/session_picker.py`, enhanced `status_bar.py`/`input_bar.py`, updated `app.py`

**Plans:** 3 plans in 3 waves — Complete

Plans:
- [x] 06-01-PLAN.md — Conversation Core (events, MessageCard, ToolCallCard, ConversationView)
- [x] 06-02-PLAN.md — Sidebar, Timeline, Enhanced Bars
- [x] 06-03-PLAN.md — Session Picker + Cleanup

---

### Phase 7: TUI Visual Overhaul

**Goal:** Transform the existing Textual TUI (Phase 6) from functional-but-minimal to professional-grade, Claude Code-inspired terminal interface. Focus is on visual design, layout simplification, and inline content rendering.

**Plans:** 3 plans in 2 waves — Complete

Plans:
- [x] 07-01-PLAN.md — Theme + Layout Foundation (Wave 1)
- [x] 07-02-PLAN.md — Inline Tool Calls (Wave 1)
- [x] 07-03-PLAN.md — Input Bar + Indicators + Wiring (Wave 2)

---

### Phase 8: TUI Conversation Layout ◆

**Goal:** Transform the conversation area so user prompts and AI responses are visually distinct in a clear chronological sequence. Add a right-side stats panel (tokens/time/model). Remove the header. Soften the window background.

**Key decisions:** No header, straight to conversation, always-visible right panel, message separation via background color, inline tool calls kept from Phase 7, softer dark background.

**Plans:** 3 plans in 2 waves — Complete

Plans:
- [x] 08-01-PLAN.md — StatsPanel Widget + Theme Foundation (Wave 1)
- [x] 08-02-PLAN.md — Message Card Bifurcation (Wave 1) — Subtle dark bg on assistant messages
- [x] 08-03-PLAN.md — Layout Restructure + Stats Wiring (Wave 2)

---

### Phase 10: Token Streaming ✓

**Goal:** Complete the token streaming pipeline built in Phase 9 — implement `stream_chat()` in the LLM client and emit `TokenProduced` events from the agent so the TUI streams tokens live. Tool-call turns stay non-streaming; partial output on cancel/error is kept in the TUI only, marked truncated.

**Canonical refs:** `.planning/phases/10-token-streaming/10-CONTEXT.md`

**Plans:** 4 plans in 4 waves — Complete 2026-07-31

Plans:
- [x] 10-01-PLAN.md — LLM client streaming (StreamChunk contract + stream_chat implementation) — Wave 1
- [x] 10-02-PLAN.md — Agent TokenProduced emission (streaming loop, no partial persistence) — Wave 2
- [x] 10-03-PLAN.md — TUI truncation marker + auto-scroll (D-04/D-06, D-07 verified) — Wave 3
- [x] 10-04-PLAN.md — End-to-end human verification (checkpoint) — Wave 4

### Phase 11: Session Popup & Panel Layout ◆

**Goal:** Reorganize the TUI so the conversation is the main panel with date/time shown in the other panel. Add `/session` (opens a small popup listing all sessions — click one to continue it) and `/new` (starts a fresh conversation) as prompt-input commands.

**Key decisions:** Conversation-first layout, date/time companion panel, `/session` popup picker, `/new` fresh conversation.

**Canonical refs:** `.planning/phases/09-ts-tui-json-rpc/09-UI-SPEC.md`, `.planning/phases/09-ts-tui-json-rpc/09-CONTEXT.md`

**Depends on:** Phase 10
**Plans:** 4/4 plans executed — Complete 2026-08-01

Plans:
- [x] 11-01-PLAN.md — Backend: context-restore fix, sessions.get RPC, auto-title (D-06/D-10/D-13) — Wave 1
- [x] 11-02-PLAN.md — TUI contracts: SessionMessage type, getSessionHistory, loadConversation (D-10) — Wave 1
- [x] 11-03-PLAN.md — /session full-screen picker + /new + honest footer (D-06..D-09, D-11/D-12) — Wave 2
- [x] 11-04-PLAN.md — Conversation-first layout + live DatePanel + E2E checkpoint (D-01..D-05, D-14..D-16) — Wave 3

</details>

### 🚧 v1.1 Skills System (In Progress)

**Milestone Goal:** Progressive-disclosure skills for AgentHarness — users author `SKILL.md` files under `.agentharness/skills/`, the agent sees a cheap budgeted manifest (name + description) in the system prompt each turn, and the full skill body loads into context only on demand (via `read_skill` or `/skill`). Six phases, dependency-ordered pure → integrated, with the highest-risk change (session serialization) placed second so the JSONL exclusion is proven before any real skill body flows.

- [x] **Phase 12: Skills Discovery & Manifest** - SKILL.md authoring, discovery with skip-and-warn, budgeted manifest in the system prompt (completed 2026-08-01)
- [x] **Phase 13: Context Plumbing (Persist Fix)** - session serialization handles skill bodies: persist in memory, never to JSONL (completed 2026-08-01)
- [ ] **Phase 14: read_skill Provider End-to-End** - path-scoped `read_skill` tool, bundled resources, system-role body injection
- [ ] **Phase 15: Session Behavior & /skill Command** - user-invocable `/skill` via the 4-layer RPC contract, loaded-skill accounting
- [ ] **Phase 16: TUI Integration (Skill Indicator)** - TUI `/skill` + visible "Skill loaded" indicator via typed event
- [ ] **Phase 17: allowed-tools Enforcement & Hardening** - tool-list filtering, intersection semantics, full E2E verification

## Phase Details

### Phase 12: Skills Discovery & Manifest
**Goal**: Users can author skills as `SKILL.md` files and the agent sees a budgeted manifest of every skill (name + description) in the system prompt each turn — progressive-disclosure Level 1. Pure domain work: zero integration risk, no harness changes.
**Depends on**: Nothing (first phase of v1.1)
**Requirements**: STORE-01, STORE-02, STORE-03, STORE-04, STORE-05, DISC-01, DISC-02
**Success Criteria** (what must be TRUE):
  1. User can author a skill as `.agentharness/skills/<name>/SKILL.md` (one folder per skill); the name is kebab-case and matches the folder, with required `name` + `description` and optional `allowed-tools` frontmatter.
  2. Agent sees a manifest listing every valid skill's `name` + `description` in the system prompt each turn — no skill body is loaded by the manifest alone.
  3. The manifest never exceeds its character budget (~1,500 chars): over-long descriptions are trimmed deterministically and trimmed skills are logged with a warning.
  4. A skill with missing/invalid frontmatter is skipped with a warning and never breaks the harness; duplicate names resolve first-wins (deterministic order) with a warning naming the shadowed skill.
**Plans**: 4 plans (finalized 2026-08-01 — waves: {12-01} → {12-02, 12-03} → {12-04}; 12-02 and 12-03 are parallel-safe, no shared files)

Plans:
- [x] 12-01: `skills/` package foundation — `PyYAML>=6.0.3` added to requirements.txt, `models.py` `SkillInfo` dataclass, `frontmatter.py` delimiter splitter (`yaml.safe_load`, degrades to `({}, body)`)
- [x] 12-02: `discovery.py` — per-skill parse+validate skip-and-warn taxonomy (`parse_skill_entry`) + deterministic first-wins scan with win32 case handling (`discover_skills`)
- [x] 12-03: `manifest.py` — `build_manifest_text` (D-11 format, D-13 None-when-empty, D-14 sanitize, D-09 char cap via `SKILL_MANIFEST_MAX_CHARS`, D-10 longest-first trim with marker + warnings)
- [x] 12-04: System-prompt integration — `Session.skill_manifest` (non-serialized field) + `# Available Skills` appended at end of `_build_system_prompt()` (D-12), barrel completion, end-to-end seam tests

### Phase 13: Context Plumbing (Persist Fix)
**Goal**: Session serialization handles loaded skill bodies safely: they persist for the session (system-role, summarization-exempt) but never serialize to the JSONL session file. Highest-risk change in the milestone — lands *before* any real skill body can flow through `to_events()`.
**Depends on**: Phase 12
**Requirements**: ACT-03, ACT-04, ACT-05
**Success Criteria** (what must be TRUE):
  1. User can save and close a session that had skill bodies loaded; the JSONL session file contains no skill content — loaded bodies are never persisted (D-13 leak closed).
  2. Repeated saves of an active session produce no missing or duplicated events — the persist filter and `mark_saved()` index stay aligned (index-drift fix, paired with the `Message.persist` filter).
  3. A conversation that crosses the summarization threshold keeps its loaded skill bodies intact — system-role exemption at `context.py:88` honored (documented, not reimplemented).
  4. Loaded skill bodies persist in memory for the entire session — every subsequent turn sees them — and vanish on `/new` or session close (session-scoped state via non-serialized `skill_manifest`/`skill_state` fields).
**Plans**: 3 plans (waves: 1 → 2 → 3; 13-01 no deps, 13-02 dep 13-01, 13-03 dep 13-02)

Plans:
- [x] 13-01: `Message.persist: bool = True` field + `persist=False` support for skill bodies
- [x] 13-02: `to_events()` persist filter + `mark_saved()` index fix (paired change; save/resume round-trip tests)
- [x] 13-03: Non-serialized `Session.skill_manifest`/`skill_state` fields + summarization-exemption documentation + unit tests

### Phase 14: read_skill Provider End-to-End
**Goal**: Agent can load a skill body on demand via a dedicated `read_skill` tool and read bundled resources through path-scoped reads — Level-2/Level-3 disclosure. Bodies flow through the persist-safe plumbing from Phase 13 as system-role messages.
**Depends on**: Phase 13
**Requirements**: DISC-03, DISC-04, DISC-05, ACT-02, CAP-01, CAP-03
**Success Criteria** (what must be TRUE):
  1. Agent can call `read_skill(name=<skill>)` and the full skill body loads into context as a system-role message exactly once when the manifest description matches the task — the tool result is a short ack, the body is not duplicated in the result (auto-invoke works).
  2. Agent can read bundled resources (`references/`, `scripts/`, `assets/`) by relative path into the skill directory — Level-3 disclosure works for markdown references (CAP-01).
  3. Every path-traversal attempt — `../`, `..\`, absolute paths, symlinks, win32 drive-path tricks — is rejected with a clear error; reads never escape the skills directory (win32 test vectors ship in the same wave as the tool).
  4. `read_skill` is a reserved, un-namespaced tool name (async provider registered as `__skills__`): no skill can shadow it, and the allowed-tools filter contract always retains it (`allowed ∪ {read_skill}`, unit-tested here).
  5. Cancelling a turn mid-load leaves no dangling tool_calls — the next turn streams cleanly (pre-existing cancel hole closed and tested).
**Plans**: 4 plans (initial estimate — refined during planning)

Plans:
- [ ] 14-01: `store.py` — `SkillStore` (index, `load`, `read_path` with canonicalize+contain traversal guard) + traversal test suite
- [ ] 14-02: `provider.py` — async `SkillToolProvider` registered as `__skills__`, reserved-name collision rejection, filter-retention contract
- [ ] 14-03: Agent integration — `RuntimeAPI.load_skill()` single shared load path, system-role body injection via tagged `add_skill_message()`, short ack tool result
- [ ] 14-04: Cancel-mid-gather fix + backend E2E (load → inject → summarize-survive → JSONL untouched)

### Phase 15: Session Behavior & /skill Command
**Goal**: Loaded-skill state becomes user-invocable and accounted: `/skill <name>` slash command via the full 4-layer RPC contract (REPL + backend), separate loaded-skill token accounting, and the combined-filter semantics decision locked before enforcement ships.
**Depends on**: Phase 14
**Requirements**: ACT-01
**Success Criteria** (what must be TRUE):
  1. User can type `/skill <name>` in the REPL and the skill loads through the same shared load path as `read_skill` — model-driven and user-driven activation cannot drift.
  2. `/skill` with an unknown name shows a distinct skill-not-found error; `/skill` with no argument shows usage — never a silent no-op or fall-through to a chat prompt.
  3. Loaded-skill tokens are accounted separately from chat tokens so the summarization threshold stays chat-relative; a loaded-skill token cap bounds context growth (no unbounded accumulation).
  4. Combined `allowed-tools` semantics across multiple loaded skills are decided and documented (intersection recommended) — the decision is recorded here so Phase 17 only implements.
**Plans**: 3 plans (initial estimate — refined during planning)

Plans:
- [ ] 15-01: `skills.load` RPC across all four layers in one change (protocol.py RPC_METHODS, adapter.py, rpc-client.ts, types.ts)
- [ ] 15-02: REPL `/skill` branch in `_handle_session_cmd` + distinct error/usage handling (non-blocking vs streaming turn)
- [ ] 15-03: `loaded_skill_tokens` accounting + loaded-skill token cap + combined-filter semantics doc (P-05/P-09/P-11)

### Phase 16: TUI Integration (Skill Indicator)
**Goal**: The TUI surfaces skill activity: `/skill <name>` works from the input bar and a visible "Skill loaded" indicator appears whenever a skill loads — driven by a typed `skill_loaded` notification, never by inference or stream pollution.
**Depends on**: Phase 15
**Requirements**: ACT-06
**Success Criteria** (what must be TRUE):
  1. User can type `/skill <name>` in the TUI input bar and the skill loads via the backend RPC — the input is intercepted like `/session`/`/new`, never forwarded as a chat prompt.
  2. TUI shows a visible "Skill loaded: <name>" indicator (footer chip / inline notice) whenever a skill loads — whether model-driven (`read_skill`) or via `/skill`.
  3. The indicator round-trips end-to-end through the typed `skill_loaded` notification: keystroke → JSON-RPC → load → notification → indicator (all five touchpoints).
  4. The indicator never pollutes the assistant message stream — no fake tool cards, no streamed text chunks, no token/tool_result smuggling.
**Plans**: 3 plans (initial estimate — refined during planning)

Plans:
- [ ] 16-01: `NotificationType.skill_loaded` across all five touchpoints (harness event → server mapping + extractor → protocol → `handleEvent` → store)
- [ ] 16-02: InputBar `/skill ` intercept (mirroring `/session`/`/new`, never falls through to `submitPrompt`)
- [ ] 16-03: "Skill loaded" indicator UI + round-trip test (keystroke → RPC → notification → indicator)
**UI hint**: yes

### Phase 17: allowed-tools Enforcement & Hardening
**Goal**: `allowed-tools` is enforced while a skill is loaded — the tool list passed to the LLM is filtered per-iteration (registry never mutated), `read_skill` always retained, intersection semantics across multiple loaded skills, and a full end-to-end verification of the whole milestone.
**Depends on**: Phase 15 (semantics decision) — also inherits load state from Phases 13-14
**Requirements**: CAP-02, CAP-04
**Success Criteria** (what must be TRUE):
  1. While a skill with `allowed-tools` is loaded, the tool list passed to the LLM is filtered to that skill's allowed set — enforced as a pure per-iteration projection; the registry is never mutated.
  2. `read_skill` remains callable during filtering, so a loaded skill can still pull references or load another skill — the Phase 14 retention contract holds under real enforcement (no deadlock).
  3. When multiple skills with `allowed-tools` are loaded, filtering uses the documented intersection semantics — the model only sees tools allowed by every loaded skill.
  4. Dispatch-side rejection in `call_tool` keeps enforcement consistent — a call to a filtered-out tool is refused even if it reaches the registry (no bypass).
  5. Full E2E verification passes end to end: author a skill → manifest visible → `/skill` force-load → system-role injection → JSONL untouched → filter active → indicator shown; `/new` resets skill state.
**Plans**: 3 plans (initial estimate — refined during planning)

Plans:
- [ ] 17-01: `filter.py` pure per-iteration projection at the `list_tools()` boundary + `read_skill` always retained + intersection semantics
- [ ] 17-02: Dispatch-side rejection in `registry.call_tool` + `switch_session()`/`/new` reset semantics
- [ ] 17-03: Milestone E2E verification script + hardening pass (remaining traversal vectors, filter edge cases)

### Future (backlog)

- Tool system hardening (remove_provider, health-check, reconnect)
- Multi-turn agent improvements
- Package restructuring
- v1.2 Skills: authoring/management UI, `/skills` listing, script-as-tool, user-global skills dir, skill chaining

## Progress

**Execution Order:**
Phases execute in numeric order: 12 → 13 → 14 → 15 → 16 → 17

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
| 10. Token Streaming | v1.0 | 4/4 | Complete | 2026-07-31 |
| 11. Session Popup & Panel Layout | v1.0 | 4/4 | Complete | 2026-08-01 |
| 12. Skills Discovery & Manifest | v1.1 | 4/4 | Complete    | 2026-08-01 |
| 13. Context Plumbing (Persist Fix) | v1.1 | 3/3 | Complete   | 2026-08-01 |
| 14. read_skill Provider End-to-End | v1.1 | 0/4 | Not started | - |
| 15. Session Behavior & /skill Command | v1.1 | 0/3 | Not started | - |
| 16. TUI Integration (Skill Indicator) | v1.1 | 0/3 | Not started | - |
| 17. allowed-tools Enforcement & Hardening | v1.1 | 0/3 | Not started | - |
