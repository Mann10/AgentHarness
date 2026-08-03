# Phase 5: Harness Runtime - Context

**Gathered:** 2026-07-25
**Status:** Ready for planning

<domain>
## Phase Boundary

Create a Harness Runtime layer between the TUI and Agent that owns request lifecycle, event distribution, session management, and background scheduling. The Runtime sits at the center of the architecture: TUI is a pure view layer, workers consume from a durable queue, and the Agent executes turns.

</domain>

<decisions>
## Implementation Decisions

### Architecture Boundary (TUI vs Runtime vs Agent)
- **D-01:** TUI is a pure view layer — no worker loops, no queue management, no agent lifecycle
- **D-02:** The harness/ module owns Runtime, EventBus, Scheduler, SessionManager, Cancellation
- **D-03:** gent/core.py stays as-is but gets event emission hooks (Agent emits events during run())
- **D-04:** jobqueue/ module is for worker/background mode only — not used by interactive TUI path

### Event Bus
- **D-05:** Lightweight in-process async EventBus — simple subscribe/publish pattern
- **D-06:** Swappable implementation (start simple, upgrade to Redis/ZeroMQ later if needed)
- **D-07:** Events: turn_started, tool_call, tool_result, response_complete, error, cancelled

### Request Queue & Scheduler
- **D-08:** Two paths: interactive prompts go directly to Scheduler (no queue); worker requests go through durable SQLite queue
- **D-09:** Scheduler dispatches one turn at a time — no concurrent agent execution
- **D-10:** Existing QueueManager + SQLiteJobStore reused for worker mode, not replaced
- **D-11:** If user submits while agent is busy, second prompt enters a simple in-memory pending backlog

### Interface (TUI ↔ Runtime)
- **D-12:** Python in-process async API — no IPC
- **D-13:** RuntimeAPI methods: submit_prompt(), cancel(), list_sessions(), switch_session()
- **D-14:** TUI subscribes to EventBus events on mount, updates chat view on each event
- **D-15:** Non-blocking — submit_prompt() returns immediately, TUI reacts to events

### OpenCode's Discretion
- Exact EventBus implementation details (subscriber management, error handling)
- Session Manager lifecycle (auto-save timing, crash recovery)
- Cancellation mechanism (asyncio task cancellation vs cooperative flag)
- Pending backlog behavior (size limit, overflow strategy)
- Existing REPL continues using direct Agent calls or adapts to Runtime

</decisions>

<specifics>
## Specific Ideas

- "I want it to work like Claude Code" — chat-based TUI with inline tool call cards and grinding indicator
- No streaming for now — use agent.run() (batch mode), show indicator while processing
- OpenCode's TUI design patterns (split-pane chat, inline tool call cards, session picker) are the UX reference

</specifics>

<canonical_refs>
## Canonical References

### Architecture discussions
- tui/app.py — Current TUI (to be refactored to pure view layer)
- agent/core.py — Agent.run() to get event emission hooks
- jobqueue/manager.py — QueueManager for worker mode persistence
- main.py — Current wiring (Runtime will own this)

### Prior context
- .planning/phases/04-textual-tui-and-queue/ — Phase 4 decisions (job queue model being adapted)
- .planning/PROJECT.md — Project vision and non-negotiables
- .planning/ROADMAP.md §Phase 4 — Prior phase deliverables

</canonical_refs>

<code_context>
## Existing Code Insights

### Reusable Assets
- jobqueue/manager.py — QueueManager with SQLite persistence, reuse for worker path
- agent/core.py — Agent.run() is batch-only, no streaming hooks yet
- tui/app.py — Current TUI has worker loops embedded, need to extract

### Established Patterns
- async/await throughout — all I/O uses asyncio
- Constructor dependency injection throughout
- Textual framework for TUI widgets

### Integration Points
- harness/ connects tui/ (event consumption) with agent/ (turn execution) and jobqueue/ (worker persistence)
- main.py creates Runtime instead of wiring everything inline
- main.py --worker path uses Runtime's queue path

</code_context>

<deferred>
## Deferred Ideas

- Streaming agent responses — future phase (requires agent/core.py changes)
- Swap TUI framework (Textual → OpenTUI) — future phase (requires IPC or WASM bridge)
- Multi-agent routing in Scheduler — future phase
- WebSocket-based remote TUI — backlog

</deferred>

---

*Phase: 05-harness-runtime*
*Context gathered: 2026-07-25*
