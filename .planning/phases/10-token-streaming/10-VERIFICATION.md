---
phase: 10-token-streaming
verified: 2026-07-31T16:00:00Z
status: passed
score: 14/14 must-haves verified
overrides_applied: 0
---

# Phase 10: Token Streaming — Verification Report

**Phase Goal:** Complete the token streaming pipeline built in Phase 9 — implement `stream_chat()` in the LLM client and emit `TokenProduced` events from the agent so the TUI streams tokens live. Tool-call turns stay non-streaming; partial output on cancel/error is kept in the TUI only, marked truncated.

**Verified:** 2026-07-31T16:00:00Z
**Status:** passed
**Re-verification:** No — initial verification

## Goal Achievement

The phase goal is **fully achieved**. Phase 9's Gap 1 ("TokenProduced event never emitted; stream_chat() raises NotImplementedError") is closed: the producer (`stream_chat`), the emitter (`_stream_llm_call`), the transport (RPC `token` notification), and the presentation (live render, auto-scroll, truncation marker) are all implemented, wired, tested, and human-verified end-to-end.

### Observable Truths

| # | Truth | Status | Evidence |
|---|-------|--------|----------|
| 1 | LLM client streams text chunks from the API as they arrive | ✓ VERIFIED | `llm/openai_client.py:101-175` — async generator over `chat.completions.create(stream=True)` (line 126), `yield StreamChunk(content=d.content)` per delta (line 145); `tests/test_stream_chat.py::test_stream_chat_yields_text_chunks` passes |
| 2 | Tool-call turns are assembled from streaming deltas and returned as tool_calls | ✓ VERIFIED | `tool_call_parts` dict keyed by `tc.index` (lines 137-156), assembled `ToolCall` list on final chunk (lines 166-175); `test_stream_chat_assembles_tool_calls` passes |
| 3 | Stream failures map to typed LLM errors (LLMConnectionError/LLMResponseError) | ✓ VERIFIED | `APIConnectionError`→`LLMConnectionError` and `APIError`→`LLMResponseError` at both create() (lines 128-135) and mid-iteration (lines 157-164); both mapping tests pass |
| 4 | Agent emits one TokenProduced event per text chunk with session_id and chunk content | ✓ VERIFIED | `agent/core.py:82-87` — `await self._emit(TokenProduced(session_id=self._session.id, chunk=chunk.content))`; `test_agent_emits_token_produced_per_chunk` passes |
| 5 | Tool-call turns emit no TokenProduced events and proceed through the existing tool-call flow | ✓ VERIFIED | `agent/core.py:88-92` — tool_calls chunk returns `LLMResponse(content=None, tool_calls=...)`; no emit for tool chunks; `test_agent_tool_turn_emits_no_token_events` passes; ToolCallEvent/ToolResultEvent flow intact (lines 153-177) |
| 6 | Partial streamed content is never added to session context on error or cancel | ✓ VERIFIED | `add_assistant_message` called only after stream completes (lines 124, 188); `test_agent_mid_stream_error_keeps_partial_out_of_context` asserts context contains only the user message; no `finally`/`except asyncio.CancelledError` added — cancellation propagates to Scheduler unchanged |
| 7 | REPL still waits for ResponseComplete and prints final text (D-08 — no token subscription added) | ✓ VERIFIED | `main.py` contains zero `TokenProduced`/`EVENT_TOKEN_PRODUCED` references; subscribes only to `"ResponseComplete"` (lines 178, 190); human step 5 APPROVED in 10-04 |
| 8 | Streamed tokens render live with the blinking cursor and the view auto-scrolls to the newest content | ✓ VERIFIED | `rpc-client.ts:217-227` `case "token"` → `startAssistantMessage` + `appendToken`; `StreamingText` blinking cursor in message.tsx; `conversation-panel.tsx:25` `flexDirection="column-reverse"` bottom-anchors newest content; human step 1 APPROVED in 10-04 |
| 9 | Partial stream is marked truncated on cancel and on error | ✓ VERIFIED | `store.truncateStreamingMessage()` in BOTH `error` and `cancelled` handlers (rpc-client.ts:249, 256); `(truncated)` marker renders in message.tsx:33-37; store action marks `isStreaming:false, truncated:true` (agent-store.ts:115-124); human step 3 APPROVED in 10-04 |
| 10 | response_complete still finalizes a streaming message to the full content (D-07) | ✓ VERIFIED | `store.completeAssistantMessage(p.content)` exactly 1 match in rpc-client.ts:239, untouched; `completeAssistantMessage` replaces content and clears isStreaming (agent-store.ts:101-113); human step 2 APPROVED in 10-04 |
| 11 | A human observes tokens streaming live in the TUI with the blinking cursor | ✓ VERIFIED | 10-04 checkpoint:human-verify — step 1 APPROVED by user (live chunk-by-chunk render, auto-scroll) |
| 12 | A human observes the conversation auto-scrolling as content streams | ✓ VERIFIED | 10-04 step 1 APPROVED (view pinned to newest content after several exchanges) |
| 13 | A human observes partial text marked truncated when cancelling mid-stream | ✓ VERIFIED | 10-04 step 3 APPROVED (partial text remains + dim-yellow italic ` (truncated)` label + "Cancelled" notice) |
| 14 | A human observes the REPL printing final text only (no streaming) | ✓ VERIFIED | 10-04 step 5 APPROVED (no token-level output; complete final text prints once on completion) |

**Score:** 14/14 truths verified

### Required Artifacts

| Artifact | Expected | Status | Details |
| -------- | ----------- | ------ | ------- |
| `llm/base.py` | StreamChunk contract + fixed stream_chat abstract signature | ✓ VERIFIED | `class StreamChunk:` (lines 10-23, content/tool_calls fields); `def stream_chat(...) -> AsyncIterator[StreamChunk]` (lines 40-47); `AsyncIterator` imported from collections.abc; `Generator` import removed |
| `llm/openai_client.py` | stream_chat implementation using AsyncOpenAI stream=True | ✓ VERIFIED | Async generator (lines 101-175); `stream=True` (line 126); both `yield StreamChunk` forms present; `_convert_tools` helper extracted and shared with `_call_sdk`; no `Generator` import |
| `tests/test_stream_chat.py` | 5 streaming tests | ✓ VERIFIED | All 5 functions present (text, tool-call assembly, connection error, stream error, tools→API kwargs); suite passes |
| `agent/core.py` | _stream_llm_call helper emitting TokenProduced | ✓ VERIFIED | Helper at lines 63-93; `TokenProduced` imported (line 14); both run() call sites stream (lines 113, 185); zero `chat_from_messages` matches |
| `tests/test_agent_streaming.py` | 4 agent streaming tests | ✓ VERIFIED | All 4 functions present (per-chunk emission, tool-turn zero tokens, mid-stream error keeps partial out, forced path) |
| `tui-ink/src/types.ts` | Message.truncated flag | ✓ VERIFIED | `truncated?: boolean` (line 78) |
| `tui-ink/src/store/agent-store.ts` | truncateStreamingMessage action | ✓ VERIFIED | Interface (line 23) + implementation (lines 115-124), no-op unless last message is live streaming assistant |
| `tui-ink/src/bridge/rpc-client.ts` | Truncation wiring on cancelled/error notifications | ✓ VERIFIED | `store.truncateStreamingMessage()` in both error and cancelled cases (2 matches); token case handler live (lines 217-227) |
| `tui-ink/src/components/message.tsx` | Truncation marker rendering | ✓ VERIFIED | `message.truncated &&` + `(truncated)` dim-yellow italic label (lines 33-37) |
| `tui-ink/src/panels/conversation-panel.tsx` | Bottom-anchored auto-scroll layout | ✓ VERIFIED | `flexDirection="column-reverse"` + `flexGrow={1}` (line 25); `[...conversation].reverse().map` (line 40); thinking indicators before, empty-state hint after (1 match) |

### Key Link Verification

| From | To | Via | Status | Details |
| ---- | --- | --- | ------ | ------- |
| `llm/openai_client.py` | openai SDK | `create(stream=True)` | ✓ WIRED | Line 126; `stream=True` literal present |
| `llm/openai_client.py` | `llm/base.py` | `yield StreamChunk` | ✓ WIRED | Lines 145 and 175; imports `StreamChunk` (line 10) |
| `agent/core.py` | `harness/events.py` | `await self._emit(TokenProduced(...))` | ✓ WIRED | Lines 83-86; `TokenProduced(` in emit call |
| `agent/core.py` | `llm/base.py` | `async for chunk in self._llm.stream_chat(...)` | ✓ WIRED | Lines 79-81 (both call sites via `_stream_llm_call`) |
| `harness/scheduler.py` | `harness/event_bus.py` | `agent._emit` → `bus.publish` | ✓ WIRED | `_emit_to_bus` wrapper (lines 49-52) — TokenProduced flows to EventBus |
| `backend/rpc/server.py` | EventBus | EVENT_TOKEN_PRODUCED subscription | ✓ WIRED | Line 164 subscribe; line 57 maps to `token` notification; `_extract_token_produced_payload` (lines 88-93) |
| `tui-ink/src/bridge/rpc-client.ts` | `tui-ink/src/store/agent-store.ts` | `case "token"` → appendToken | ✓ WIRED | Lines 217-227; also `truncateStreamingMessage` from error/cancelled cases |
| `tui-ink/src/store/agent-store.ts` | `tui-ink/src/components/message.tsx` | conversation state → MessageCard | ✓ WIRED | Store state consumed via `useAgentStore` in conversation-panel; message.tsx renders truncated flag |
| `tui-ink/src/panels/conversation-panel.tsx` | `tui-ink/src/components/message.tsx` | reversed list in column-reverse Box | ✓ WIRED | `[...conversation].reverse().map(<MessageCard>)` inside `column-reverse` Box |

### Data-Flow Trace (Level 4)

| Artifact | Data Variable | Source | Produces Real Data | Status |
| -------- | ------------- | ------ | ------------------ | ------ |
| `agent/core.py` TokenProduced emission | chunk | `stream_chat()` async generator over real SDK stream | ✓ FLOWING | Real delta content from `d.content`; no static fallbacks |
| `backend/rpc/server.py` token notification | payload | EventBus → `_extract_token_produced_payload` | ✓ FLOWING | session_id/chunk/request_id from live event |
| `tui-ink/src/bridge/rpc-client.ts` token handler | p.chunk | NDJSON line from Python subprocess stdout | ✓ FLOWING | Parses real notification; routes to store |
| `agent-store.ts` appendToken | chunk | token handler call | ✓ FLOWING | Appends to live streaming assistant message |
| `conversation-panel.tsx` | conversation | useAgentStore | ✓ FLOWING | Renders real accumulated streamed content; human-verified live with real LLM (10-04) |
| Truncation path | truncated flag | truncateStreamingMessage action | ✓ FLOWING | Set only on real error/cancelled notifications; marker renders |

### Behavioral Spot-Checks

| Behavior | Command | Result | Status |
| -------- | ------- | ------ | ------ |
| Full Python suite passes | `python -m pytest tests/ -q` | 43 passed in 4.95s | ✓ PASS |
| TypeScript compiles | `npm run typecheck` (tui-ink) | 0 errors | ✓ PASS |
| Build produces output | `npm run build` (tui-ink) | dist/index.js 23.27 KB | ✓ PASS |
| No chat_from_messages in agent | `rg "chat_from_messages" agent/core.py` | 0 matches | ✓ PASS |
| No Generator remnants in LLM client | `rg "Generator" llm/base.py llm/openai_client.py` | 0 matches | ✓ PASS |
| Truncation wired in both handlers | `rg -c "truncateStreamingMessage" rpc-client.ts` | 2 matches | ✓ PASS |
| D-07 intact | `rg -c "completeAssistantMessage\(p.content\)" rpc-client.ts` | 1 match | ✓ PASS |
| D-08 REPL untouched | `rg "TokenProduced" main.py` | 0 matches | ✓ PASS |
| All 5 stream_chat tests present | `rg "def test_" tests/test_stream_chat.py` | 5 functions | ✓ PASS |
| All 4 agent streaming tests present | `rg "def test_" tests/test_agent_streaming.py` | 4 functions | ✓ PASS |
| Phase commits in git log | `git log --oneline` | 5de9041, ec6452f, 2f10579, f9ed130, 45ce45a, b580776, ecf47c0 all present | ✓ PASS |

### Requirements Coverage (D-01..D-08 cross-reference)

Every decision D-01..D-08 from 10-CONTEXT.md is claimed by at least one plan and verified in code. No orphaned requirements.

| Requirement | Source Plans | Description | Status | Evidence |
| ----------- | ------------ | ----------- | ------ | -------- |
| D-01 | 10-01, 10-02 | Agent streams every LLM call via the streaming path | ✓ SATISFIED | Both run() call sites use `_stream_llm_call` (agent/core.py:113, 185); zero `chat_from_messages` in agent |
| D-02 | 10-02 | TokenProduced emitted only for text content | ✓ SATISFIED | Emit guarded by `if chunk.content` (line 82); tool-call turns emit zero (test + human step 4) |
| D-03 | 10-01, 10-02 | Client distinguishes turn type by inspecting stream deltas | ✓ SATISFIED | `stream_chat` inspects `d.content`/`d.tool_calls` (openai_client.py:144-146); agent never pre-decides (docstring lines 71-73) |
| D-04 | 10-03, 10-04 | Partial text stays visible in TUI, marked truncated | ✓ SATISFIED | `truncateStreamingMessage` + `(truncated)` marker; human step 3 APPROVED |
| D-05 | 10-02 | Partial content not persisted to session JSONL | ✓ SATISFIED | `add_assistant_message` only after stream completes; test asserts partial absent from context on error |
| D-06 | 10-03, 10-04 | Chunk-by-chunk live rendering, auto-scrolling to bottom | ✓ SATISFIED | appendToken per chunk + StreamingText cursor; column-reverse auto-scroll; human steps 1-2 APPROVED |
| D-07 | 10-03, 10-04 | On response_complete, streamed message finalized to full content | ✓ SATISFIED | `completeAssistantMessage(p.content)` 1 match, untouched; human step 2 APPROVED |
| D-08 | 10-02, 10-04 | Streaming is TUI-only; REPL keeps batch behavior | ✓ SATISFIED | main.py zero TokenProduced refs, subscribes only to ResponseComplete; human step 5 APPROVED |

### Anti-Patterns Found

| File | Line | Pattern | Severity | Impact |
| ---- | ---- | ------- | -------- | ------ |
| `llm/openai_client.py` | 171 | `json.loads` on tool-call args outside try/except (WR-02) | ⚠️ Warning | Malformed model JSON surfaces as raw `JSONDecodeError` instead of mapped `LLMResponseError`; agent's `except Exception` still emits ErrorEvent (no crash, no data loss). Deliberate per plan — mirrors `_call_sdk` line-84 behavior. Not a goal blocker. |
| `agent/core.py` | 92 | Text content accompanying tool calls dropped on mixed turns (WR-01) | ⚠️ Warning | Preamble text streamed to TUI but not persisted to history (`content=None`). Acknowledged edge-case drift — plan explicitly stated "do not flag at verification" (D-01/D-02 never require mixed-turn behavior). Not a goal blocker. |
| `agent/core.py` + `tui-ink` | 153-177, 203-215 | Tool call IDs never reach TUI; results matched by tool name (WR-03) | ⚠️ Warning | Pre-existing from Phase 9, not introduced by this phase; affects multi-call display correctness only. Not a goal blocker. |
| `tui-ink/src/panels/conversation-panel.tsx` | 1 | Unused `useEffect`/`useRef` imports (IN-01) | ℹ️ Info | Compiles silently (no noUnusedLocals); cosmetic |
| `tui-ink/src/store/agent-store.ts` | 112 | `status: content ? "idle" : "idle"` dead ternary (IN-02) | ℹ️ Info | Both branches identical; cosmetic |
| `tui-ink/src/bridge/rpc-client.ts` | 50 | stderr log stream: relative path, never closed, no error handler (IN-03) | ℹ️ Info | Pre-existing from Phase 9; adjacent to TUI work, not this phase's scope |
| `agent/core.py` | 88 | `is not None` treats empty `tool_calls: []` as tool turn (IN-04) | ℹ️ Info | Shipped `OpenAIClient` can't produce `[]` (guarded by `if tool_call_parts:`); only affects non-conforming clients |

No TODO/FIXME/placeholder markers, no `NotImplementedError` remnants, no hardcoded-empty stub returns in any phase-modified file.

### Human Verification Record (closed during 10-04 checkpoint)

The 10-04 plan was a `checkpoint:human-verify` gate (blocking). All 6 manual steps were completed by a human at a real terminal with a real LLM and **APPROVED by the user** (recorded in 10-04-SUMMARY.md). No failure symptoms were recorded, so no gap-closure plan was spawned. The four human-observable truths (truths 11-14) are verified by this approval record:

1. TUI live chunk-by-chunk token streaming with blinking green cursor — ✅ APPROVED
2. TUI auto-scroll keeps newest content visible after several exchanges — ✅ APPROVED
3. Ctrl+C mid-stream → partial text remains + ` (truncated)` label + Cancelled notice — ✅ APPROVED
4. Tool-call turn shows indicator, no streaming cursor during tool turn — ✅ APPROVED
5. REPL prints final text once on completion, no token-level output — ✅ APPROVED
6. Both TUI and REPL launch cleanly — ✅ APPROVED

### Gaps Summary

**No gaps.** All 14 must-have truths verified, all 9 key links wired, the full data flow (agent → EventBus → RPC `token` notification → TUI store → render) is live and human-confirmed. Phase 9 Gap 1 ("TokenProduced event never emitted") is closed — `stream_chat()` is a real implementation and `TokenProduced` events are emitted per text chunk. The 3 code-review warnings (WR-01/02/03) are non-blocking: WR-01 is an explicitly acknowledged edge-case drift, WR-02 is a deliberate error-mapping choice with a safety net (ErrorEvent), and WR-03 is pre-existing from Phase 9. All 8 locked decisions D-01..D-08 are honored and verified.

---

_Verified: 2026-07-31T16:00:00Z_
_Verifier: OpenCode (gsd-verifier)_
