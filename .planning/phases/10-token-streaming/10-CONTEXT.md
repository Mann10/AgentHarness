# Phase 10: Token Streaming - Context

**Gathered:** 2026-07-31
**Status:** Ready for planning

<domain>
## Phase Boundary

Make token output stream live to the terminal UI. The full pipeline (`TokenProduced` event → RPC `token` notification → TUI store `appendToken` → `StreamingText` render) was built in Phase 9 but is dead code — `stream_chat()` raises `NotImplementedError` and the agent never emits `TokenProduced`. This phase completes that pipeline end-to-end. REPL, worker, and session/context behavior stay unchanged except where noted.

</domain>

<decisions>
## Implementation Decisions

### Streaming scope
- **D-01:** Agent streams every LLM call via the streaming path (no batch-first/re-generate approach)
- **D-02:** `TokenProduced` events are emitted **only for text content**. Tool-call turns produce no token events (their content is null anyway) and proceed through the existing tool-call flow unchanged
- **D-03:** The client distinguishes turn type by inspecting stream deltas (content vs tool_calls) — the agent never pre-decides

### Stream interruption (cancel/error mid-stream)
- **D-04:** Partial text already streamed stays visible in the TUI, marked as truncated (user-visible marker, e.g. label or styling)
- **D-05:** Partial content is **not persisted** to session JSONL. Session context only receives complete assistant messages on `ResponseComplete`. Resuming a session does not restore partial text

### TUI presentation
- **D-06:** Chunk-by-chunk live rendering as tokens arrive (existing `appendToken` + `StreamingText` blinking cursor), auto-scrolling to bottom
- **D-07:** On `response_complete`, the streamed message is finalized to the full content (existing `completeAssistantMessage` behavior)

### Mode coverage
- **D-08:** Streaming is TUI-only. Python REPL keeps batch `Thinking...` indicator and prints final text on completion. Worker mode unchanged

### OpenCode's Discretion
- Exact `stream_chat()` implementation in `openai_client.py` (delta accumulation, tool-call detection, how turn-type is conveyed to the agent — sentinel, final value, or attribute)
- Whether `stream_chat` takes `context` or `messages`; fixing its sync `Generator` signature to async
- How truncation is marked in the TUI (text label vs styling)
- Auto-scroll implementation detail in Ink
- Chunk flush cadence / batching

</decisions>

<specifics>
## Specific Ideas

- "Finish what we built" — Phase 9 explicitly deferred agent changes; this closes that gap
- No new UI patterns requested — reuse the existing `isStreaming`/`StreamingText` path already in `tui-ink`

</specifics>

<canonical_refs>
## Canonical References

**Downstream agents MUST read these before planning or implementing.**

### Streaming contract (already built)
- `harness/events.py` — `TokenProduced` event (line 64) + `EVENT_TOKEN_PRODUCED` (line 75)
- `backend/rpc/server.py` — subscription (line 164), mapping (line 57), `_extract_token_produced_payload` (line 88)

### Backend to implement
- `llm/openai_client.py` — `stream_chat()` stub raising `NotImplementedError` (lines 95-98); `_call_sdk()` pattern for request building/error mapping
- `llm/base.py` §`stream_chat` — abstract signature (lines 24-26), currently sync `Generator` — needs async
- `agent/core.py` — agent loop (`run()`, lines 61-172), emit callback pattern, tool-call turn flow
- `harness/scheduler.py` — wires `agent._emit` → `bus.publish` (lines 49-52)

### TUI (already handles tokens — reference, minimal/no changes)
- `tui-ink/src/bridge/rpc-client.ts` — `token` event handler (lines 217-227)
- `tui-ink/src/store/agent-store.ts` — `startAssistantMessage`/`appendToken`/`completeAssistantMessage`
- `tui-ink/src/components/streaming-text.tsx` — blinking cursor render
- `tui-ink/src/panels/conversation-panel.tsx` — message list render

### Prior phase decisions
- `.planning/phases/09-ts-tui-json-rpc/09-CONTEXT.md` — D-07 (TokenProduced), D-08/D-09 (notification design), D-26/D-27 (log hygiene)
- `.planning/phases/09-ts-tui-json-rpc/09-VERIFICATION.md` — Gap 1: "TokenProduced event never emitted" (the exact defect this phase fixes)
- `.planning/phases/05-harness-runtime/05-CONTEXT.md` — D-03 (agent emit hooks), deferred "Streaming agent responses — future phase"

</canonical_refs>

<code_context>
## Existing Code Insights

### Reusable Assets
- `TokenProduced` event + RPC `token` forwarding — fully wired, just needs a producer
- TUI `token` handler + store streaming actions — fully implemented in `tui-ink`
- Agent `emit` callback → EventBus → RPC pipeline — working for 6 event types already
- `AsyncOpenAI.chat.completions.create(stream=True)` — SDK supports streaming natively

### Established Patterns
- Async emit callback on Agent, wired to EventBus publish in Scheduler
- EventBus → RPC notification → typed payload extractor → TUI store reducer
- Constructor dependency injection, async-first everywhere

### Integration Points
- `llm/openai_client.py stream_chat` — the only unimplemented producer
- `agent/core.py` loop — switch LLM call to streaming path, emit `TokenProduced` per chunk
- Cancellation: `CancellationToken`/`CancelledError` from Scheduler must interrupt the stream and leave partial TUI content marked truncated

</code_context>

<deferred>
## Deferred Ideas

- Token streaming in the Python REPL — user chose TUI-only for this phase
- Persisting partial/cut-off messages to session history — user chose display-only
- Streaming in worker/background mode — future concern

</deferred>

---

*Phase: 10-token-streaming*
*Context gathered: 2026-07-31*
