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

### Future (backlog)

- Testing infrastructure
- Tool system hardening (remove_provider, health-check, reconnect)
- Multi-turn agent improvements
- Package restructuring
