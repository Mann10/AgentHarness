---
phase: 16-tui-integration-skill-indicator
plan: 04
subsystem: ui
tags: [ink, rpc-client, agent-store, streaming, backwards-scan, skill_loaded, session-scope, cr-01, wr-05]

# Dependency graph
requires:
  - phase: 16-tui-integration-skill-indicator
    provides: skill_loaded notification across all five touchpoints (16-01), InputBar /skill intercept (16-02), footer chip + notice tones + baseline human E2E (16-03), CR-01/WR-05 gaps flagged in 16-VERIFICATION.md
provides:
  - Stream-safety (CR-01 closed): token and response_complete handlers scan the conversation BACKWARDS for the last streaming assistant, and the store's appendToken/completeAssistantMessage/truncateStreamingMessage target that exact message via the shared lastStreamingIdx helper — a mid-stream `/skill` notice can no longer spawn a second assistant box or strand the original with isStreaming: true
  - Session-scoped chip (WR-05 closed): skill_loaded updates the chip only when params.request_id === state.activeSessionId — a stale notification arriving after a session switch cannot re-add a previous session's skill
  - Dead `busy` destructure removed from app.tsx (WR-03 closed): mid-turn loads are now safe via the scan fix, not via a (permanently-false) gate
affects: [16-tui-integration-skill-indicator, 17-allowed-tools-enforcement-hardening]

# Tech tracking
tech-stack:
  added: [] # no new dependencies — fix is algorithmic (backwards scan) + store index targeting
  patterns:
    - "Backwards scan for the last `assistant && isStreaming` message: `[...conversation].reverse().find(...)` in both streaming event handlers — notices interleaved mid-stream never change which box receives tokens/completion"
    - "Shared `lastStreamingIdx` module-level helper in agent-store.ts — handler scan is only effective if the store actions target the same message, so appendToken/completeAssistantMessage/truncateStreamingMessage all index via the helper instead of `msgs[msgs.length - 1]`"
    - "Session-correlation guard on notifications that carry a request_id (backend session id): `params.request_id === state.activeSessionId` before mutating session-scoped state"

key-files:
  created: []
  modified:
    - tui-ink/src/bridge/rpc-client.ts
    - tui-ink/src/store/agent-store.ts
    - tui-ink/src/app.tsx

key-decisions:
  - "CR-01 fix (reviewer-suggested): token and response_complete handlers scan backwards for the last streaming assistant (`lastStreaming`), only calling startAssistantMessage()/addAssistantMessage() when none exists — a notice at the tail can no longer force a duplicate assistant box"
  - "Store actions use a shared lastStreamingIdx helper (appendToken / completeAssistantMessage / truncateStreamingMessage) so tokens are appended to, and completion/truncation clears, the exact streaming message wherever it sits — a mid-stream notice at the array tail can no longer make tokens drop or completion skip"
  - "WR-05 fix: skill_loaded guards `params.request_id === state.activeSessionId` before addLoadedSkill — a late notification from a previous session cannot re-add its skill to the chip (loadConversation/resetConversation already clear loadedSkills)"
  - "WR-03 fix: the dead `const { busy }` destructure in app.tsx InputBar is removed — busy is permanently false (setBusy(true) is never called, grep-verified), so gating `/skill` on it would refuse every load; the scan fix provides safety instead"

patterns-established:
  - "Streaming mutations target the last streaming assistant by index, never the array tail — interleaved notice messages are safe by construction (D-04 ack path preserved verbatim)"
  - "Notification side effects that touch session-scoped state are gated on request_id === activeSessionId"

requirements-completed: [ACT-06]

# Metrics
duration: 4min
completed: 2026-08-04
---

# Phase 16 Plan 04: Gap Closure (CR-01 + WR-05) — Stream-Safe `/skill` During Streaming Summary

**Backwards-scan stream-safety: the token/response_complete handlers and the store's streaming mutations now target the last streaming assistant wherever it sits, so a mid-stream `/skill` notice can no longer spawn a second assistant box or strand the original with a stuck spinner; the skill_loaded chip update is session-scoped — closed by an approved 8-step human E2E (task 3)**

## Performance

- **Duration:** 4 min (continuation segment — task 3 E2E approval + SUMMARY; tasks 1-2 executed in the prior session)
- **Started:** 2026-08-04T22:14:00Z (continuation)
- **Completed:** 2026-08-04T22:17:36Z
- **Tasks:** 3 (2 committed + 1 human-approved checkpoint)
- **Files modified:** 3

## Accomplishments

- **CR-01 closed (stream corruption under mid-stream load):** both `token` and `response_complete` in `rpc-client.ts` now scan the conversation backwards for the last `assistant && isStreaming` message instead of only inspecting the tail. `startAssistantMessage()` is called only when no streaming box exists, and `addAssistantMessage()` only when the scan finds none — so a `✓ Loaded skill` notice interleaved mid-stream can no longer force a second ▸ assistant box or leave the original stranded with `isStreaming: true`. Verified by human E2E steps 3-5 (twice, two skills).
- **Store-side index targeting (makes the handler scan effective):** a module-level `lastStreamingIdx(msgs)` helper in `agent-store.ts` returns the index of the last streaming assistant; `appendToken`, `completeAssistantMessage`, and `truncateStreamingMessage` all operate on that exact message instead of `msgs[msgs.length - 1]` — a notice at the array tail can no longer silently drop tokens, skip completion, or fail to truncate (E2E steps 4-5, 7). The degenerate `status: content ? "idle" : "idle"` ternary (IN-01) was replaced with a plain `status: "idle"`.
- **WR-05 closed (session-scoped chip):** `skill_loaded` now guards `params.request_id === state.activeSessionId` before `addLoadedSkill` — an in-flight notification arriving after a `/new` or session switch cannot re-add the previous session's skill to the chip (E2E step 8).
- **WR-03 closed (dead code removed):** the unused `const { busy }` destructure in `app.tsx` InputBar is gone. `busy` is permanently `false` (`setBusy(true)` is never called anywhere — grep confirms only `setBusy(false)` call sites), so gating `/skill` on it would have refused every load; the scan fix provides the safety instead.
- **Human E2E approved (task 3, blocking checkpoint):** all 8 manual checks passed — `/skill <name>` DURING an active stream shows the ✓ notice + chip with **no second assistant box**, the stream completes in a single box with no stranded spinner (twice, two skills), already_loaded stays a dim no-op, cancel truncates cleanly with no stray box, and `/new` + reload is session-scoped.

## Verification Results

| Check | Result |
|-------|--------|
| `cd tui-ink && npm run typecheck` | PASS (0 errors) |
| `cd tui-ink && npm run build` | PASS (tsup dist emits, 44.57 KB) |
| `lastStreaming` x4 in rpc-client.ts (2 handlers × declaration+usage) | PASS |
| `params.request_id === state.activeSessionId` x1 in rpc-client.ts | PASS |
| `lastStreamingIdx` x4 in agent-store.ts (1 helper def + 3 action usages) | PASS |
| `const { busy }` x0 in app.tsx | PASS |
| `startAssistantMessage()` x1 in rpc-client.ts (only inside `if (!lastStreaming)` guard) | PASS |
| `msgs[msgs.length - 1]` x0 (non-comment) in agent-store.ts | PASS |
| IN-01 degenerate ternary x0 in agent-store.ts | PASS |
| `python -m pytest tests/test_skill_loaded_notification.py -q` | PASS (9 passed) |
| Human E2E 8-step checklist (task 3) | PASS — APPROVED by user, 8/8 checks |
| `graphify update .` (AGENTS.md convention) | PASS (no topology changes detected — no new code from continuation) |

## task Commits

Each task was committed atomically:

1. **task 1: Stream-safety scan in rpc-client token + response_complete + skill_loaded session guard** - `40d12ed` (fix)
2. **task 2: Store streaming actions target the last streaming assistant + remove dead busy destructure** - `b87cf52` (fix)
3. **task 3: Human E2E re-check — `/skill <name>` DURING streaming (CR-01 trigger)** - `APPROVED` (blocking human-verify checkpoint — no commit; all 8 manual checks passed)

**Plan metadata:** `docs(16-04)` (final commit — this SUMMARY + state updates)

## Files Created/Modified

- `tui-ink/src/bridge/rpc-client.ts` - `token` and `response_complete` handlers scan backwards (`lastStreaming`) for the last streaming assistant; `skill_loaded` guards `params.request_id === state.activeSessionId` before `addLoadedSkill`
- `tui-ink/src/store/agent-store.ts` - module-level `lastStreamingIdx(msgs)` helper; `appendToken`/`completeAssistantMessage`/`truncateStreamingMessage` target that index; IN-01 degenerate ternary removed (`status: "idle"`)
- `tui-ink/src/app.tsx` - dead `const { busy }` destructure removed from InputBar (WR-03)

## Decisions Made

- **Backwards scan for the last streaming assistant (CR-01):** both streaming event handlers use `[...state.conversation].reverse().find((m) => m.role === "assistant" && m.isStreaming)` instead of the tail-only `lastMsg` check — the reviewer-suggested fix from 16-REVIEW. A notice interleaved mid-stream is now inert w.r.t. box selection.
- **Shared `lastStreamingIdx` helper in the store:** the handler scan alone is insufficient if the store still mutates `msgs[msgs.length - 1]` — the three streaming actions must target the same message the handler identified, wherever it sits. One helper, three call sites.
- **Session-scoped `skill_loaded` (WR-05):** `params.request_id === state.activeSessionId` before `addLoadedSkill` — late notifications from a prior session can no longer re-add a stale skill to the chip.
- **Dead `busy` destructure removed (WR-03):** `busy` is permanently `false` (grep-verified: no `setBusy(true)` call sites), so gating `/skill` on it would refuse every load — the scan fix provides safety, not a gate. The store field and `setBusy(false)` calls remain.

## Deviations from Plan

None - plan executed exactly as written. (Tasks 1-2 per the plan's specified code; task 3 human E2E approved with all 8 checks passing. Note: the plan's pre-implementation grep estimate "lastStreaming x2" reflects only the declarations; the actual committed code — matching the plan's code verbatim — has 4 occurrences across the two handlers (declaration + usage each), consistent with the orchestrator's post-completion expectation of 4.)

## Issues Encountered

None. The blocking human-verify checkpoint (task 3) was the only pause point and it passed on user approval.

## User Setup Required

None - no external service configuration required.

## Next Phase Readiness

- **CR-01 closed with actionable evidence:** the phase-gate human E2E (task 3) was **APPROVED** — all 8 checks passed: mid-stream `/skill` shows notice + chip with NO second assistant box, stream completes single-box with no stranded spinner (twice, two skills), already_loaded is a dim no-op, cancel truncates cleanly, `/new` is session-scoped. Plus grep gates, typecheck, tsup build, and the 9-test notification suite all pass.
- **WR-05 closed:** session-scoped chip guard verified by E2E step 8 (`/new` then immediate `/skill` → chip correct, no stale skill).
- **WR-03 closed:** dead `busy` destructure removed; mid-turn loads are safe via the scan fix.
- **Phase 16 is now fully complete** (16-01 through 16-05 all have SUMMARYs; 16-VERIFICATION.md gaps CR-01, WR-03, WR-04, WR-05 all closed). Onward to Phase 17 (allowed-tools Enforcement & Hardening).

## Self-Check: PASSED

- SUMMARY.md exists: `.planning/phases/16-tui-integration-skill-indicator/16-04-SUMMARY.md`
- Task commit exists: `40d12ed` (fix(16-04): scan backwards for last streaming assistant)
- Task commit exists: `b87cf52` (fix(16-04): target last streaming assistant in store mutations, drop dead busy destructure)
- Modified files exist: `tui-ink/src/bridge/rpc-client.ts`, `tui-ink/src/store/agent-store.ts`, `tui-ink/src/app.tsx`

---
*Phase: 16-tui-integration-skill-indicator*
*Completed: 2026-08-04*
