---
phase: 09-ts-tui-json-rpc
plan: 01
subsystem: rpc
tags: json-rpc, ndjson, stdio, python, event-bus, streaming

requires:
  - phase: 05-harness-runtime
    provides: RuntimeAPI, EventBus, SessionManager, typed domain events

provides:
  - backend/rpc/ module (protocol.py, dispatcher.py, adapter.py, server.py)
  - TokenProduced domain event for streaming
  - create_session() and delete_session() on RuntimeAPI
  - --rpc CLI flag entry point

affects:
  - 09-02 (TypeScript RPC client + transport)
  - TypeScript TUI screens (09-03 onward)

tech-stack:
  added: []
  patterns:
    - JSON-RPC 2.0 over stdin/stdout with NDJSON framing
    - EventBus subscription for typed domain event forwarding
    - Adapter pattern wrapping RuntimeAPI without modification
    - Dispatcher pattern for method routing (no business logic)

key-files:
  created:
    - backend/rpc/__init__.py
    - backend/rpc/protocol.py
    - backend/rpc/dispatcher.py
    - backend/rpc/adapter.py
    - backend/rpc/server.py
  modified:
    - harness/events.py
    - harness/runtime.py
    - harness/__init__.py
    - main.py

key-decisions:
  - "Dataclasses for JSON-RPC message schemas (consistency with existing event model, not Pydantic)"
  - "Module-level _write_json() function ensures every stdout write is flushed (no inline print())"
  - "Dispatcher pattern keeps routing logic isolated from RuntimeAPI and RPCAdapter"
  - "Event-to-notification mapping uses a dict constant + per-type payload extractor functions"
  - "request_id in notifications defaults to event.session_id with event.event_id as fallback"

patterns-established:
  - "Adapter pattern: RPCAdapter wraps RuntimeAPI without modifying it — all 7 methods are pure delegation"
  - "Dispatcher pattern: method registry with async dispatch, standard JSON-RPC error codes"
  - "Stdio transport: sys.stdout.write + sys.stdout.flush() for every message, asyncio.to_thread for blocking stdin reads"
  - "Event forwarding: EventBus subscription → _event_to_notification → _write_json pipeline"

requirements-completed:
  - D-01 (backend/rpc/ module)
  - D-02 (RuntimeAPI unchanged)
  - D-03 (Single event notification)
  - D-05 (NDJSON over stdio)
  - D-06 (RPC method surface)
  - D-07 (TokenProduced event)
  - D-08 (Event-to-notification mapping)
  - D-09 (Notification types)
  - D-20 (--rpc flag)
  - D-24 (Transport-agnostic adapter)

duration: 22min
completed: 2026-07-27
---

# Phase 9 Plan 1: Python JSON-RPC 2.0 Backend Adapter

**JSON-RPC 2.0 adapter layer over stdin/stdout with typed event notification forwarding, TokenProduced streaming event, RuntimeAPI session management methods, and --rpc CLI entry point**

## Performance

- **Duration:** 22 min
- **Started:** 2026-07-27T21:52:00Z
- **Completed:** 2026-07-27T22:14:00Z
- **Tasks:** 3
- **Files modified:** 9

## Accomplishments

- **TokenProduced event** added to harness/events.py with session_id, chunk, request_id fields — enables token-level streaming in the TUI
- **create_session() and delete_session()** added to RuntimeAPI — enables the TypeScript TUI to manage sessions via RPC
- **backend/rpc/protocol.py** — JSON-RPC 2.0 message schemas (RPCRequest, RPCResponse, RPCError, RPCNotification, EventPayload) with NotificationType StrEnum and RPC_METHODS constant list of 7 methods
- **backend/rpc/dispatcher.py** — Pure routing layer: registers handler callables by method name, dispatches with async support, returns standard JSON-RPC error codes (-32700, -32600, -32601, -32602, -32603)
- **backend/rpc/adapter.py** — RuntimeAPI wrapper with all 7 handler methods (chat, cancel, sessions.*, ping) — pure delegation, no business logic
- **backend/rpc/server.py** — Stdio RPCServer that reads JSON-RPC requests from stdin, dispatches to RuntimeAPI, forwards all 7 EventBus domain events as NDJSON notifications with typed payloads
- **main.py --rpc flag** — New entry point mode that starts RuntimeAPI and RPCServer for subprocess consumption

## Commits

Each task was committed atomically:

1. **Task 1: Add TokenProduced event + create_session/delete_session RuntimeAPI methods** - `021cfb0` (feat)
2. **Task 2: Create backend/rpc/ module — protocol, dispatcher, adapter** - `3b47ffa` (feat)
3. **Task 3: Create RPCServer (stdio loop), event forwarding, --rpc flag in main.py** - `463a63a` (feat)

## Files Created/Modified

- `backend/rpc/__init__.py` — Module exports with __all__
- `backend/rpc/protocol.py` — JSON-RPC 2.0 dataclasses, NotificationType, RPC_METHODS
- `backend/rpc/dispatcher.py` — Method registry + async dispatch with error handling
- `backend/rpc/adapter.py` — RuntimeAPI wrapper with 7 handler methods
- `backend/rpc/server.py` — Stdio read/write loop, event subscription + forwarding pipeline
- `harness/events.py` — Added TokenProduced event class + EVENT_TOKEN_PRODUCED constant
- `harness/runtime.py` — Added create_session() and delete_session() methods
- `harness/__init__.py` — Added TokenProduced and EVENT_TOKEN_PRODUCED to exports
- `main.py` — Added --rpc flag and run_rpc() function

## Deviations from Plan

None - plan executed exactly as written.

## Issues Encountered

- `backend/rpc/__init__.py` imported `RPCServer` from `server.py` before it was created (Task 2 __init__.py referenced Task 3's server). Resolved by temporarily removing the RPCServer import in Task 2 and adding it back in Task 3.

## User Setup Required

None - no external service configuration required.

## Threat Surface

No new threat surface beyond what's documented in the plan's threat model. All stdin/stdout IPC is local to the same user session.

## Next Phase Readiness

- Python backend is ready for the TypeScript RPC client: `backend/rpc/` module handles all 7 methods and streams 7 event types
- Ready for Plan 09-02: TypeScript RPC client + stdio transport in `frontend/`
- All 57 existing tests pass with no regressions

---

*Phase: 09-ts-tui-json-rpc*
*Completed: 2026-07-27*
