---
phase: 09-ts-tui-json-rpc
verified: 2026-07-27T23:30:00Z
status: gaps_found
score: 22/23 must-haves verified
overrides_applied: 0
gaps:
  - truth: "TokenProduced event is emitted during agent streaming"
    status: failed
    reason: "TokenProduced event class exists and RPC server subscribes to it, but no code path ever instantiates or publishes this event. The agent/core.py uses non-streaming chat_from_messages(), and LLM stream_chat() raises NotImplementedError. Infrastructure is complete but emission is dead code."
    artifacts:
      - path: "harness/events.py"
        issue: "TokenProduced class defined"
      - path: "backend/rpc/server.py"
        issue: "Subscribes to EVENT_TOKEN_PRODUCED but never receives it"
      - path: "agent/core.py"
        issue: "Does not emit TokenProduced events"
      - path: "llm/openai_client.py"
        issue: "stream_chat() raises NotImplementedError"
    missing:
      - "Emit TokenProduced events from agent loop or LLM streaming path"
      - "Wire stream_chat() to call event_bus.publish(TokenProduced(...))"
  - truth: "React component unmount properly cleans up RPC subscriptions"
    status: failed
    reason: "App.tsx useEffect registers 7 event subscriptions inside an async IIFE and attempts to return cleanup from the IIFE's inner return function, but the actual useEffect cleanup only sets cancelled=true. The unsubscribe functions are never called. However, the process-kill cleanup in the other useEffect prevents memory leaks since the backend process terminates."
    artifacts:
      - path: "frontend/src/App.tsx"
        issue: "Subscription cleanup functions from c.on() are returned from async IIFE's inner return, not from useEffect's return. They are never executed."
    missing:
      - "Store unsub references in refs and call them from the actual useEffect cleanup"
human_verification:
  - test: "Run the TUI and verify CTRL+C sends cancel to backend"
    expected: "Backend receives cancel request and stops processing"
    why_human: "Requires running the TUI and confirming cancel behavior"
  - test: "Run the TUI and verify session management (switch/create/delete)"
    expected: "Sessions list, create new, switch between, delete — all via RPC"
    why_human: "Requires running the TUI interacting with actual backend"
  - test: "Verify all 7 notification types flow through to UI rendering"
    expected: "Messages display, streaming shows tokens, tool calls show indicators"
    why_human: "Requires a live conversation with tool-using LLM to trigger all event types"
  - test: "Verify backend crash detection shows error bar and disconnects"
    expected: "Killing the Python subprocess shows 'Backend process disconnected' banner"
    why_human: "Requires manual process kill to trigger crash detection path"
---

# Phase 9: TypeScript TUI + JSON-RPC Adapter — Verification Report

**Phase Goal:** Add a JSON-RPC adapter layer to the existing Python backend runtime, then build a new TypeScript/Ink terminal UI that communicates exclusively over stdin/stdout JSON-RPC. The existing Python REPL and Textual TUI remain unchanged as fallbacks.

**Verified:** 2026-07-27T23:30:00Z
**Status:** gaps_found
**Re-verification:** No — initial verification

## Goal Achievement

The phase goal is **substantially achieved** — the Python JSON-RPC 2.0 adapter layer and TypeScript/Ink TUI are both built and properly wired. Two non-blocking gaps exist (see below), neither prevents the core architecture from functioning.

### Observable Truths

| # | Truth | Status | Evidence |
|---|-------|--------|----------|
| 1 | `backend/rpc/` module exists with all 5 files | ✓ VERIFIED | `__init__.py`, `protocol.py`, `dispatcher.py`, `adapter.py`, `server.py` all exist and are substantive |
| 2 | TokenProduced event defined in `harness/events.py` | ✓ VERIFIED | `class TokenProduced(HarnessEvent)` at line 64, `EVENT_TOKEN_PRODUCED` constant at line 75 |
| 3 | TokenProduced event is emitted during agent streaming | ✗ FAILED | Event defined, RPC server subscribes to it, but NO code path publishes it. `agent/core.py` uses non-streaming `chat_from_messages()`. `stream_chat()` raises `NotImplementedError`. Infrastructure complete but dead. |
| 4 | `create_session()` and `delete_session()` added to RuntimeAPI | ✓ VERIFIED | `runtime.py` lines 94-111 — delegates to SessionManager |
| 5 | `--rpc` CLI flag works in `main.py` | ✓ VERIFIED | `main.py` line 303 adds argument, line 326 dispatches to `run_rpc()` at line 278 |
| 6 | Python backend can start in `--rpc` mode | ✓ VERIFIED | `run_rpc()` creates RuntimeAPI + RPCServer, enters stdio read loop |
| 7 | All 7 RPC methods implemented | ✓ VERIFIED | `adapter.py` registers: chat, cancel, sessions.{list,switch,create,delete}, ping |
| 8 | All 7 notification types forwarded as JSON-RPC notifications | ✓ VERIFIED | `server.py` subscribes to all 7 domain events, maps to notification types with payload extractors |
| 9 | Frontend project exists with TypeScript + Ink + esbuild toolchain | ✓ VERIFIED | `frontend/package.json`, `tsconfig.json`, `esbuild.config.mjs`, `dist/index.js` (23KB) |
| 10 | TypeScript compilation passes with 0 errors | ✓ VERIFIED | `npm run typecheck` exits cleanly |
| 11 | Build succeeds | ✓ VERIFIED | `npm run build` produces `dist/index.js` |
| 12 | Frontend never imports Python logic (D-15) | ✓ VERIFIED | `grep` for Python imports in frontend returns only `PYTHON_COMMAND` string constant |
| 13 | StdioTransport spawns Python subprocess | ✓ VERIFIED | `transport.ts` uses `child_process.spawn()` with `python/python3 -m agentharness --rpc` |
| 14 | RpcClient sends requests and routes event notifications | ✓ VERIFIED | `client.ts` — `request()` method, `on()` registration, `_dispatchEvent()` |
| 15 | State store exists with pub-sub pattern (D-14) | ✓ VERIFIED | `store.ts` — `Store` class with `subscribe()`, `setState()`, 7 convenience methods |
| 16 | Reducers handle all 7 notification types (D-12) | ✓ VERIFIED | `reducers.ts` — `handleEvent()` switch covers all 7 types, no Ink/React imports |
| 17 | Message card with role-based styling | ✓ VERIFIED | `MessageCard.tsx` — user (green), assistant (cyan), error (red), system (yellow/dim) |
| 18 | Input bar with keyboard input via useInput | ✓ VERIFIED | `InputBar.tsx` — Enter submits, Backspace deletes, disabled state |
| 19 | ConversationScreen renders messages + streaming + input | ✓ VERIFIED | `ConversationScreen.tsx` — message list, streaming content, error display, InputBar |
| 20 | ToolCallIndicator, StatsBar, ErrorBar, SessionPicker exist | ✓ VERIFIED | All 4 components exist and are substantive |
| 21 | App.tsx orchestrates full process lifecycle | ✓ VERIFIED | Spawn → ping readiness → subscribe 7 events → CTRL+C cancel → crash detection → cleanup on unmount |
| 22 | CTRL+C sends cancel request (not default exit) | ✓ VERIFIED | `index.tsx` has `exitOnCtrlC: false`, `App.tsx` sends `client.request('cancel')` on Ctrl+C |
| 23 | All 57 existing tests still pass | ✓ VERIFIED | `pytest` returns "57 passed in 4.22s" |

**Score:** 22/23 truths verified

### Required Artifacts

| Artifact | Expected | Status | Details |
| -------- | -------- | ------ | ------- |
| `backend/rpc/__init__.py` | Module exports | ✓ VERIFIED | Exports all 5 classes + constants |
| `backend/rpc/protocol.py` | Message schemas | ✓ VERIFIED | 4 dataclasses, NotificationType enum, RPC_METHODS list |
| `backend/rpc/dispatcher.py` | Method routing | ✓ VERIFIED | `Dispatcher` with register/dispatch, async support, error codes |
| `backend/rpc/adapter.py` | RuntimeAPI wrapper | ✓ VERIFIED | 7 handler methods, pure delegation |
| `backend/rpc/server.py` | Stdio server | ✓ VERIFIED | Read loop, event subscription, notification forwarding |
| `harness/events.py` (TokenProduced) | Streaming event | ✓ VERIFIED | Defined but NOT emitted — see gap |
| `harness/runtime.py` (+create/delete) | Session management | ✓ VERIFIED | `create_session()` and `delete_session()` methods |
| `main.py` (--rpc) | Entry point | ✓ VERIFIED | `run_rpc()` function, `--rpc` flag |
| `frontend/src/rpc/protocol.ts` | TS types | ✓ VERIFIED | Full JSON-RPC 2.0 types + constants |
| `frontend/src/rpc/transport.ts` | Stdio transport | ✓ VERIFIED | `StdioTransport` class |
| `frontend/src/rpc/client.ts` | RPC client | ✓ VERIFIED | `RpcClient` with request/notify/on |
| `frontend/src/state/store.ts` | State store | ✓ VERIFIED | Pub-sub store with 7 convenience methods |
| `frontend/src/state/reducers.ts` | Event reducers | ✓ VERIFIED | Pure function, 7 notification types, no React/Ink imports |
| `frontend/src/ui/components/MessageCard.tsx` | Message display | ✓ VERIFIED | Role-based styling |
| `frontend/src/ui/components/InputBar.tsx` | Text input | ✓ VERIFIED | useInput hook, Enter/Backspace |
| `frontend/src/ui/screens/ConversationScreen.tsx` | Main screen | ✓ VERIFIED | Messages, streaming, errors, input |
| `frontend/src/ui/components/ToolCallIndicator.tsx` | Tool status | ✓ VERIFIED | Spinner/check/cross per status |
| `frontend/src/ui/components/StatsBar.tsx` | Status bar | ✓ VERIFIED | Session name, connection, processing |
| `frontend/src/ui/components/ErrorBar.tsx` | Error display | ✓ VERIFIED | Dismissable red box |
| `frontend/src/ui/screens/SessionPicker.tsx` | Sessions UI | ✓ VERIFIED | Keyboard-navigable list, create/switch/delete |
| `frontend/src/App.tsx` | Root component | ✓ VERIFIED | Process lifecycle, event subscription, all components wired |
| `frontend/src/index.tsx` | Entry point | ✓ VERIFIED | Ink render, exitOnCtrlC: false |

### Key Link Verification

| From | To | Via | Status | Details |
| ---- | --- | --- | ------ | ------- |
| `adapter.py` | `runtime.py` | RuntimeAPI delegation | ✓ WIRED | `self._runtime.submit_prompt()`, `cancel()`, `list_sessions()`, etc. |
| `server.py` | `event_bus.py` | EventBus subscription | ✓ WIRED | 7 `subscribe()` calls for all domain events |
| `server.py` | `sys.stdin/stdout` | NDJSON read/write | ✓ WIRED | `stdin.readline()`, `stdout.write() + flush()` |
| `transport.ts` | Python subprocess | `child_process.spawn()` | ✓ WIRED | Spawns `python -m agentharness --rpc` |
| `client.ts` | `transport.ts` | send/receive | ✓ WIRED | Request/response dispatch, event routing |
| `App.tsx` | `client.ts` | Event subscriptions | ⚠️ PARTIAL | 7 subscriptions registered, cleanup functions not called on unmount |
| `App.tsx` | `reducers.ts` | `handleEvent()` | ✓ WIRED | All 7 notification types routed to store mutations |
| `reducers.ts` | `store.ts` | Store mutations | ✓ WIRED | addMessage, appendStreamedContent, finalizeStream, etc. |
| `ConversationScreen.tsx` | `store.ts` | `store.subscribe()` | ✓ WIRED | Tick counter triggers re-render on state changes |

### Data-Flow Trace (Level 4)

| Artifact | Data Variable | Source | Produces Real Data | Status |
| -------- | ------------- | ------ | ------------------ | ------ |
| `server.py` | Event payloads | EventBus subscription | ✓ FLOWING | Events come from agent → EventBus → RPC server → stdout |
| `transport.ts` | NDJSON lines | stdout of Python subprocess | ✓ FLOWING | Real data from backend forwarded as JSON lines |
| `client.ts` | Event dispatch | transport.onMessage | ✓ FLOWING | Parses NDJSON, dispatches to registered handlers |
| `store.ts` | `StoreState` | Event handlers | ✓ FLOWING | Receives real event data, updates state |
| `ConversationScreen.tsx` | messages | store.getState() | ✓ FLOWING | Renders state store messages |
| TokenProduced emission | chunk | Agent loop | ✗ DISCONNECTED | Event defined, subscribed, handled — but never published |

### Behavioral Spot-Checks

| Behavior | Command | Result | Status |
| -------- | ------- | ------ | ------ |
| Python tests pass | `pytest` | 57 passed in 4.22s | ✓ PASS |
| TypeScript compiles | `npm run typecheck` | 0 errors | ✓ PASS |
| Build produces output | `npm run build` | dist/index.js (23KB) | ✓ PASS |
| Frontend files exist | glob | All 14 source files present | ✓ PASS |
| Backend files exist | glob | All 5 Python files present | ✓ PASS |
| All 14 commits present | `git log` | All phase commits verified | ✓ PASS |

### Requirements Coverage

| Requirement | Source Plan | Description | Status | Evidence |
| ----------- | ----------- | ----------- | ------ | -------- |
| D-01 | 09-01 | backend/rpc/ module | ✓ SATISFIED | 5 files created |
| D-02 | 09-01 | RuntimeAPI unchanged | ✓ SATISFIED | RPCAdapter wraps, doesn't modify |
| D-03 | 09-01 | Single event notification | ✓ SATISFIED | All events use `"event"` method with typed payload |
| D-05 | 09-01 | NDJSON over stdio | ✓ SATISFIED | NDJSON framing, flush after every message |
| D-06 | 09-01 | RPC method surface | ✓ SATISFIED | 7 methods implemented |
| D-07 | 09-01 | TokenProduced event | ⚠️ PARTIAL | Event defined + RPC wired, but NOT emitted |
| D-08 | 09-01 | Event-to-notification mapping | ✓ SATISFIED | `_DOMAIN_TO_NOTIFICATION` dict + payload extractors |
| D-09 | 09-01 | Notification types | ✓ SATISFIED | 7 types match D-09 spec |
| D-10 | 09-02 | frontend/ with React + Ink | ✓ SATISFIED | package.json, rendering setup |
| D-11 | 09-02/03 | Custom terminal components | ✓ SATISFIED | MessageCard, InputBar, ToolCallIndicator, etc. |
| D-12 | 09-02/03 | App logic independent of Ink/React | ✓ SATISFIED | reducers.ts has zero Ink/React imports |
| D-13 | 09-02 | Frontend structure: rpc/, state/, ui/ | ✓ SATISFIED | Directory structure matches spec |
| D-14 | 09-03 | State store — presentation only | ✓ SATISFIED | StoreState has only UI-relevant fields |
| D-15 | 09-02 | Frontend never imports Python logic | ✓ SATISFIED | Verified via grep — no Python imports |
| D-16 | 09-04 | TS TUI spawns Python subprocess | ✓ SATISFIED | `new RpcClient(PYTHON_COMMAND, ['-m', 'agentharness', '--rpc'])` |
| D-17 | 09-04 | stdin/stdout connection | ✓ SATISFIED | StdioTransport uses pipe stdio |
| D-18 | 09-04 | Kill subprocess on exit | ✓ SATISFIED | `client.stop()` on unmount with SIGTERM |
| D-20 | 09-01 | `--rpc` flag | ✓ SATISFIED | main.py line 303 |
| D-21 | 09-04 | Migration order | ✓ SATISFIED | RPC adapter → client → screens → parity |
| D-24 | 09-01 | Transport-agnostic adapter | ✓ SATISFIED | Adapter pattern, no transport coupling |

### Anti-Patterns Found

| File | Line | Pattern | Severity | Impact |
| ---- | ---- | ------- | -------- | ------ |
| `frontend/src/App.tsx` | 39-52 | Subscription cleanup uncalled | ⚠️ Warning | Event subscriptions not cleaned on unmount; mitigated by process kill |
| `agent/core.py` | 79-81 | No TokenProduced emission | ⚠️ Warning | Streaming infrastructure is dead code; TUI will never receive `token` events |
| `llm/openai_client.py` | 95-98 | stream_chat not implemented | ⚠️ Warning | Pre-requisite for TokenProduced emission; not in phase scope |
| `frontend/src/App.tsx` | 48-53, 62 | Return value of async IIFE discarded | ℹ️ Info | Inner `return () => { ... }` from async IIFE is never registered as useEffect cleanup |

### Human Verification Required

| # | Test | Expected | Why Human |
|---|------|----------|-----------|
| 1 | Run `python -m agentharness --rpc` and send a JSON-RPC ping via stdin | Backend responds with `{"result": {"status": "ok"}}` | Requires running backend and sending test input |
| 2 | Run the TUI (`node dist/index.js` from frontend/) and verify it starts | TUI displays "AgentHarness" header, StatsBar with connection status | Visual rendering verification |
| 3 | Send a chat prompt in the TUI | Prompt appears as user message (green), assistant response streams (if LLM configured) | Requires running LLM; token streaming verification |
| 4 | Press Ctrl+C during processing | Backend receives cancel request (no crash) | Behavioral test of CTRL+C interception |
| 5 | Open session picker (Ctrl+S) | Session listings appear, keyboard navigation works | Interactive UI verification |
| 6 | Kill the Python subprocess manually | ErrorBar shows "Backend process disconnected." | Crash detection pathway |

### Gaps Summary

**Gap 1 — TokenProduced event never emitted (BLOCKER? NO — WARNING)**
The streaming infrastructure is fully built: `TokenProduced` event class defined, RPC server subscribes and forwards it, TUI client handles it. But no code path ever instantiates or publishes the event. The `agent/core.py` loop uses non-streaming `chat_from_messages()`, and `llm/openai_client.py`'s `stream_chat()` raises `NotImplementedError`. This means token-level streaming will not work in the TUI until the agent is updated to emit `TokenProduced` events. However, this gap is outside the phase scope (the phase explicitly states "no changes to... Agent, tools, sessions, or memory") — the phase delivered the infrastructure, not the agent-level streaming.

**Gap 2 — Subscription cleanup in App.tsx is dead code (WARNING)**
The `useEffect` in App.tsx registers 7 event subscriptions inside an async IIFE and attempts to return cleanup from the IIFE's inner `return`, but the outer `useEffect` return only sets `cancelled = true`. The unsubscribe functions are never called. This does not cause memory leaks because the process-kill cleanup in the second `useEffect` terminates the backend process. Still, it should be fixed for correctness.

---

_Verified: 2026-07-27T23:30:00Z_
_Verifier: OpenCode (gsd-verifier)_
