# AgentHarness Roadmap

**Updated:** 2026-07-27

## Phases

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

**Plans:** 8 plans in 5 waves

Plans:
- [x] 05-00-PLAN.md — Test infrastructure (pytest.ini, conftest.py)
- [x] 05-01-PLAN.md — EventBus + Events + Cancellation
- [x] 05-02-PLAN.md — SessionManager
- [x] 05-03-PLAN.md — Agent event emission hooks
- [x] 05-04-PLAN.md — Scheduler (one-turn dispatch + backlog)
- [x] 05-05-PLAN.md — RuntimeAPI + harness/__init__.py
- [ ] 05-06-PLAN.md — TUI refactor to pure view layer
- [ ] 05-07-PLAN.md — main.py Runtime wiring

---

### Phase 6: Rich Textual TUI

**Goal:** Transform the minimal Textual TUI into a professional-grade terminal interface with rich components — conversation view with Markdown rendering, inline collapsible tool call cards, job queue sidebar, tool call timeline, session picker modal, and enhanced status/input bars. All widgets driven by the existing EventBus.

**Deliverables:** `tui/widgets/conversation_view.py`, `tui/widgets/message_card.py`, `tui/widgets/tool_call_card.py`, `tui/widgets/job_queue_sidebar.py`, `tui/widgets/tool_timeline.py`, `tui/screens/session_picker.py`, enhanced `status_bar.py`/`input_bar.py`, updated `app.py`

**Plans:** 3 plans in 3 waves

Plans:
- [x] 06-01-PLAN.md — Conversation Core (events, MessageCard, ToolCallCard, ConversationView)
- [x] 06-02-PLAN.md — Sidebar, Timeline, Enhanced Bars
- [x] 06-03-PLAN.md — Session Picker + Cleanup

---

### Phase 7: TUI Visual Overhaul

**Goal:** Transform the existing Textual TUI (Phase 6) from functional-but-minimal to professional-grade, Claude Code-inspired terminal interface. Focus is on visual design, layout simplification, and inline content rendering.

**Plans:** 3 plans in 2 waves

Plans:
- [ ] 07-01-PLAN.md — Theme + Layout Foundation (Wave 1)
- [ ] 07-02-PLAN.md — Inline Tool Calls (Wave 1)
- [ ] 07-03-PLAN.md — Input Bar + Indicators + Wiring (Wave 2)

---

### Phase 8: TUI Conversation Layout ◆

**Goal:** Transform the conversation area so user prompts and AI responses are visually distinct in a clear chronological sequence. Add a right-side stats panel (tokens/time/model). Remove the header. Soften the window background.

**Key decisions:** No header, straight to conversation, always-visible right panel, message separation via background color, inline tool calls kept from Phase 7, softer dark background.

**Plans:** 3 plans in 2 waves

**Wave 2 *(blocked on Wave 1 completion)***

**Cross-cutting constraints:** "StatsPanel is visible and shows data", "Messages are visually distinct by type"

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

**Requirements**: TBD
**Depends on:** Phase 10
**Plans:** 4 plans

Plans:
- [ ] 11-01-PLAN.md — Backend: context-restore fix, sessions.get RPC, auto-title (D-06/D-10/D-13) — Wave 1
- [ ] 11-02-PLAN.md — TUI contracts: SessionMessage type, getSessionHistory, loadConversation (D-10) — Wave 1
- [ ] 11-03-PLAN.md — /session full-screen picker + /new + honest footer (D-06..D-09, D-11/D-12) — Wave 2
- [ ] 11-04-PLAN.md — Conversation-first layout + live DatePanel + E2E checkpoint (D-01..D-05, D-14..D-16) — Wave 3

---

### Future (backlog)

- Tool system hardening (remove_provider, health-check, reconnect)
- Multi-turn agent improvements
- Package restructuring
