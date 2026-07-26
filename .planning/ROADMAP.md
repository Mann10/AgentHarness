# AgentHarness Roadmap

**Updated:** 2026-07-25

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
- [ ] 05-00-PLAN.md — Test infrastructure (pytest.ini, conftest.py)
- [ ] 05-01-PLAN.md — EventBus + Events + Cancellation
- [ ] 05-02-PLAN.md — SessionManager
- [x] 05-03-PLAN.md — Agent event emission hooks
- [ ] 05-04-PLAN.md — Scheduler (one-turn dispatch + backlog)
- [ ] 05-05-PLAN.md — RuntimeAPI + harness/__init__.py
- [ ] 05-06-PLAN.md — TUI refactor to pure view layer
- [ ] 05-07-PLAN.md — main.py Runtime wiring

---

### Future (backlog)

- Tool system hardening (remove_provider, health-check, reconnect)
- Multi-turn agent improvements
- Package restructuring
