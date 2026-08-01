---
phase: 11-session-popup-and-panel-layout
plan: 02
subsystem: api
tags: [tui, ink, typescript, rpc, zustand, sessions.get]

# Dependency graph
requires:
  - phase: 11-session-popup-and-panel-layout
    provides: sessions.get RPC + context-restore fix + auto-title (Plan 01 backend)
provides:
  - SessionMessage / SessionHistoryResponse wire contracts (roles user|assistant only)
  - RpcClient.getSessionHistory with {error} dict discrimination before {messages} cast
  - loadConversation store action seeding non-streaming conversation with full state reset
affects: [11-03 SessionPicker overlay, 11-04 panel layout + date/time panel]

# Tech tracking
tech-stack:
  added: []
  patterns:
    - "Client-side wire contract typed first, backend implements the same shape in parallel"
    - "Backend error-dict discrimination (\"error\" in result) instead of relying on JSON-RPC errors"
    - "Non-streaming history ingest mirroring resetConversation to protect token-streaming logic"

key-files:
  created: []
  modified:
    - tui-ink/src/types.ts
    - tui-ink/src/bridge/rpc-client.ts
    - tui-ink/src/store/agent-store.ts

key-decisions:
  - "SessionMessage locks roles to user|assistant — system summaries and tool results are skipped at ingest (UI-SPEC §10), structural typing tolerates extra backend keys"
  - "getSessionHistory throws on backend {error} dicts so a failure never reaches the store as conversation data (T-11-05)"
  - "loadConversation mirrors resetConversation (toolCalls/toolCallCount/status/error) and ingests non-streaming messages; timestamps = Date.now() at ingest, ordering from array order"

patterns-established:
  - "Interface-first ordering: picker and layout build against typed contracts from this plan"

requirements-completed: [D-10]

# Metrics
duration: 2min
completed: 2026-08-01
---

# Phase 11 Plan 02: History Contracts Summary

**SessionMessage/SessionHistoryResponse wire types, RpcClient.getSessionHistory with backend error-dict discrimination, and loadConversation store ingest with full tool/streaming state reset — the typed client surface Plan 03 (picker) and Plan 04 (layout) build against.**

## Performance

- **Duration:** 2 min
- **Started:** 2026-08-01T07:22:55Z
- **Completed:** 2026-08-01T07:24:49Z
- **Tasks:** 3
- **Files modified:** 3

## Accomplishments

- `SessionMessage` (`role: "user" | "assistant"`, `content`) and `SessionHistoryResponse` (`messages: SessionMessage[]`) exported from `types.ts` — the `sessions.get` wire contract locked to UI-SPEC §10
- `RpcClient.getSessionHistory(sessionId)` calls `request("sessions.get", { session_id })` and throws on `{"error": ...}` dicts (T-11-05 mitigation) before casting to `{ messages }`
- `loadConversation(messages: SessionMessage[])` store action seeds `conversation` with non-streaming messages and resets `toolCalls`, `toolCallCount`, `status`, `error` (research Pitfall 4 — protects the `token` event handler's `lastMsg.role !== "assistant"` tail logic)

## Task Commits

Each task was committed atomically:

1. **task 1: history payload types** - `76090fb` (feat)
2. **task 2: RpcClient.getSessionHistory** - `02c294e` (feat)
3. **task 3: store loadConversation action** - `243620a` (feat)

**Plan metadata:** (final docs commit, see below)

## Files Created/Modified

- `tui-ink/src/types.ts` - Added `SessionMessage` and `SessionHistoryResponse` interfaces after `SessionSummary`; existing types untouched
- `tui-ink/src/bridge/rpc-client.ts` - Extended type import with `SessionMessage`; added `getSessionHistory` after `deleteSession` with `"error" in result` discrimination
- `tui-ink/src/store/agent-store.ts` - Imported `SessionMessage`; declared `loadConversation` in `AgentActions`; implemented it after `resetConversation`

## Decisions Made

- Roles locked to `user`/`assistant` per UI-SPEC §10 — no `tool`/`system` roles in the ingest contract; extra backend per-message keys tolerated by TS structural typing on read
- Error discrimination `"error" in result` required: the backend adapter returns `{"error": "..."}` dicts (not JSON-RPC error responses) for missing/invalid/not-found params
- Ingested messages are non-streaming (no `isStreaming`/`truncated`) with `Date.now()` timestamps; ordering comes from array order, not timestamps
- Full state reset on ingest (mirrors `resetConversation`) so stale tool/streaming state never leaks from a previous session

## Deviations from Plan

None - plan executed exactly as written.

## Issues Encountered

None.

## User Setup Required

None - no external service configuration required.

## Next Phase Readiness

- Ready for Plan 03 (SessionPicker overlay): `getSessionHistory` + `loadConversation` + `switchSession` are all available and typecheck-clean
- Ready for Plan 04 (panel layout): store `sessions`/`activeSessionId` selectors untouched and compatible
- Backend `sessions.get` RPC implemented in Plan 01 (Wave 1 parallel) — client and server shapes match per UI-SPEC §10

---

*Phase: 11-session-popup-and-panel-layout*
*Completed: 2026-08-01*

## Self-Check: PASSED

- FOUND: tui-ink/src/types.ts (SessionMessage, SessionHistoryResponse exports)
- FOUND: tui-ink/src/bridge/rpc-client.ts (getSessionHistory)
- FOUND: tui-ink/src/store/agent-store.ts (loadConversation)
- Commits verified: `76090fb`, `02c294e`, `243620a`
- `npm run typecheck` 0 errors; `npm run build` succeeds
