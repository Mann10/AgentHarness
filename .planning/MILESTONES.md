# Milestones

## v1.0 AgentHarness MVP (Shipped: 2026-08-01)

**Phases completed:** 10 phases, 25 plans, 50 tasks

**Key accomplishments:**

- Six typed event dataclasses, async EventBus with subscriber isolation, and CancellationToken with cooperative cancel/wait/reset
- RuntimeAPI orchestrator class owning EventBus, Scheduler, SessionManager, and Agent with lazy-import barrel exports and full test coverage
- Subtle dark background ($surface) on assistant messages via --assistant-bg CSS class; user messages remain transparent. CSS class wiring for existing theme rules. No labels, no alignment changes.
- StreamChunk dataclass contract in llm/base.py plus a stream_chat async generator over AsyncOpenAI stream=True — per-delta text yields for text turns, single assembled ToolCall chunk for tool-call turns, with typed error mapping matching _call_sdk
- Agent loop routed through `stream_chat()` via a new `_stream_llm_call` helper that emits `TokenProduced` per text chunk, with tool-call turns untouched and a fully green 43-test suite
- Streamed token output stays visible and marked truncated on cancel/error (dim-yellow italic `(truncated)` label), and the conversation panel auto-scrolls via bottom-anchored column-reverse layout, while response_complete finalization (D-07) is verified intact
- Live chunk-by-chunk token streaming with blinking cursor, auto-scroll, truncation-on-cancel, non-streaming tool-call turns, and REPL batch printing all confirmed working by a human at a real terminal with a real LLM — 6/6 manual steps APPROVED, zero defects recorded, no gap-closure plan needed
- Backend session-continue foundation: `switch_session` context-restore fix (load + `restore_context` before Agent creation), 8th RPC method `sessions.get` returning chronological history with a path-traversal guard, and first-prompt auto-title (D-13) on the submit path — all covered by 11 new tests (43 → 54 suite).
- SessionMessage/SessionHistoryResponse wire types, RpcClient.getSessionHistory with backend error-dict discrimination, and loadConversation store ingest with full tool/streaming state reset — the typed client surface Plan 03 (picker) and Plan 04 (layout) build against.
- Full-screen switch-only SessionPicker overlay opened by /session, immediate /new fresh-chat command, and honest footer hints — all driven by the Wave-1 contracts (getSessionHistory RPC client, loadConversation store action, SessionMessage types)
- Conversation owns the screen with a passive live-clock DatePanel on the right; the always-visible SessionPanel is gone; the phase is human-verified end-to-end.

**Follow-up quick task (260801-jra):** session name now shows in the conversation panel/header/date-panel immediately on the first question — synchronous auto-title persistence in `submit_prompt`, TUI sessions refresh after /new and each submit, and a new `sessions.active` RPC binding the runtime's active session on connect.

**Known deferred items at close:** 2 (see STATE.md Deferred Items — debug `enter-not-submitting`, Phase 09 verification gap).

---
