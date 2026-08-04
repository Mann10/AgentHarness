---
phase: 16-tui-integration-skill-indicator
reviewed: 2026-08-04T00:00:00Z
depth: standard
files_reviewed: 4
files_reviewed_list:
  - tui-ink/src/app.tsx
  - tui-ink/src/bridge/rpc-client.ts
  - tui-ink/src/components/footer.tsx
  - tui-ink/src/store/agent-store.ts
findings:
  critical: 1
  warning: 6
  info: 6
  total: 13
status: issues_found
---

# Phase 16: Code Review Report

**Reviewed:** 2026-08-04T00:00:00Z
**Depth:** standard
**Files Reviewed:** 4 (gap-closure deltas on top of the 12-file 16-01..16-03 review)
**Status:** issues_found

## Summary

Re-reviewed the complete `skill_loaded` pipeline plus the Phase 16 gap-closure deltas (plans 16-04 and 16-05) against the four changed files: `rpc-client.ts` (CR-01 backwards-scan in `token`/`response_complete`, WR-05 `request_id === activeSessionId` guard on `skill_loaded`), `agent-store.ts` (`lastStreamingIdx` helper threading through `appendToken`/`completeAssistantMessage`/`truncateStreamingMessage`, IN-01 ternary removed), `app.tsx` (dead `busy` destructure dropped), and `footer.tsx` (WR-04 honest width budget with `string-width` display columns).

**Gap-closure verdict — substantively correct.** The CR-01 fix holds up under trace: the handler backwards-scan and the store `lastStreamingIdx` helper target the same message (both scans run on the same synchronous call stack, so they cannot disagree), and a mid-stream notice no longer spawns a second assistant box, drops tokens, or strands the original with `isStreaming: true`. The WR-05 guard is correctly wired — backend `_event_to_notification` sets `request_id = session_id`, and `SkillLoadedEvent` carries `session.id`, so `params.request_id === state.activeSessionId` is a valid session correlation (verified against `backend/rpc/server.py`). The WR-04 budget is now honest: `W = columns - CHIP_PADDING_X*2 - stringWidth("Skill: ")` = `columns - 9`, which exactly covers the rendered `<Box paddingX={1}>` + label, so a passing chip cannot wrap. All fit comparisons use `stringWidth` (display columns), fixing the UTF-16 undercount for CJK/emoji skill names. The dead `busy` destructure removal is correct — grep confirms `setBusy(true)` has zero call sites, so `busy` is permanently `false` and a gate would have refused every load.

**No new critical defects introduced by the gap-closure.** Two new quality findings: `string-width` is imported directly in footer.tsx but is not declared in `package.json` (it is only a transitive Ink dependency — fragile against Ink dependency changes), and the mid-turn `/skill` chip timing caveat remains undocumented (see WR-03 closure note). Findings resolved by this pass: CR-01, WR-03 (dead destructure), WR-04, WR-05, IN-01. Findings still open (untouched by gap-closure): WR-01, WR-02, WR-06, IN-02..IN-05. CR-01 is preserved below as the historical record with the verified fix.

## Critical Issues

### CR-01: Skill notice added mid-stream strands the streaming assistant message — FIXED and verified in 16-04

**File:** `tui-ink/src/bridge/rpc-client.ts:236-247` (token), `248-268` (response_complete); `tui-ink/src/store/agent-store.ts:51-56, 99-132`
**Issue:** Original finding (16-01..16-03): a mid-stream `/skill` notice made the tail-only handlers spawn a second assistant box and strand the original with `isStreaming: true`. **Closed by 16-04** — `token` and `response_complete` now scan backwards for the last `assistant && isStreaming` message, and the store actions index the same message via `lastStreamingIdx`. Verified: typecheck/build pass, human E2E (8 steps) approved, no second-box/spinner-strand reproduction in the traced paths.
**Remaining note (not a defect):** the token handler appends via two store updates per event (`startAssistantMessage()` + `appendToken()`). This is not a correctness issue (both run in the same synchronous handler, so no interleaving is possible), and the `idx !== -1` guard in `appendToken` makes the second update a no-op when the first didn't apply — acceptable defense-in-depth.

## Warnings

### WR-01: JSON-RPC error code discarded — forces fragile verbatim-string equality (OPEN — untouched by gap-closure)

**File:** `tui-ink/src/bridge/rpc-client.ts:179-180` (dependent: `tui-ink/src/app.tsx:89-93`)
**Issue:** `pending.reject(new Error((msg.error as { message?: string }).message ?? "RPC error"))` throws away `msg.error.code` (-32001 SKILL_NOT_FOUND, etc.). app.tsx:89 then discriminates on exact message equality — any backend rewording silently converts the D-04 bare-copy branch into the generic `SKILL_LOAD_FAILED` wrapper. The gap-closure pass did not touch this path.
**Fix:** Preserve the code and branch on it:
```ts
if (msg.error) {
  const e = new Error((msg.error as { message?: string }).message ?? "RPC error") as Error & { code?: number }
  e.code = (msg.error as { code?: number }).code
  pending.reject(e)
}
// app.tsx:
if (err.code === -32001) { s.addSkillNotice(`Skill '${name}' not found`, "error") }
```

### WR-02: tool_call_id dropped at add-time — tool results matched by tool *name* (OPEN — untouched by gap-closure)

**File:** `tui-ink/src/store/agent-store.ts:134-149, 151-174` (dependent: `tui-ink/src/bridge/rpc-client.ts:222-223, 233-234`)
**Issue:** `addToolCall(name, args, callId)` never stores the backend's `tool_call_id` (parameter unused). `updateToolResult`/`setToolCallError` match `tc.name === callId || tc.id === callId`, and rpc-client.ts passes `p.tool_name` as `callId`. Two calls to the same tool in one turn overwrite each other's results and durations. Pre-existing; not in the gap-closure scope.
**Fix:** Store `callId` on the tool-call record and match exclusively on it.

### WR-03: `/skill` intercept gating — dead `busy` destructure removed; mid-turn chip timing caveat remains (CLOSED for the dead code, caveat below)

**File:** `tui-ink/src/app.tsx:34` (destructure removed)
**Issue:** The dead `const { busy }` destructure is gone (16-04). This closure is sound: grep confirms `setBusy(true)` has zero call sites, so `busy` is permanently `false` and a gate would have refused every load. The remaining semantic caveat: `/skill` during an in-flight turn lights the chip immediately while the running model may have already snapshotted its context — the skill body is in `session.context`, so the chip claim is accurate for the *session*, but the *current* turn may not see it until the next one. This is a documented design decision (16-04 SUMMARY, "mid-turn loads are safe via the scan fix"), not a bug — tracked as IN-06 below rather than a warning.
**Fix:** None required for correctness; consider a one-line hint in the chip row or notice copy if users need the next-turn semantics spelled out.

### WR-04: Footer chip width budget — fixed; new dependency-declaration defect (gap-closure pass)

**File:** `tui-ink/src/components/footer.tsx:1, 18-28`
**Issue:** The original budget defect (`columns - 4`, UTF-16 `.length`) is fixed: `W = columns - CHIP_PADDING_X*2 - stringWidth(CHIP_LABEL + " ")` = `columns - 9`, exactly matching the rendered `paddingX={1}` + label, and all fit checks use `stringWidth`. **However, the fix introduces a new defect:** `import stringWidth from "string-width"` (line 1) is a direct import of a module that is NOT declared in `tui-ink/package.json` `dependencies` — it resolves only because Ink happens to depend on it transitively. Any future Ink release that drops or restructures that transitive dependency breaks `npm run build`/`typecheck` with a module-not-found error, and the current declaration does not pin a version. The 16-05 SUMMARY itself claims "no new dependency" while adding one.
**Fix:** Declare it explicitly:
```json
// tui-ink/package.json dependencies
"string-width": "^7.0.0"
```

### WR-05: `skill_loaded` session correlation — FIXED and verified (16-04)

**File:** `tui-ink/src/bridge/rpc-client.ts:284-294`
**Issue:** Original finding: the handler ignored `params.request_id` and set the chip unconditionally, so a notification in flight across a session switch re-added the previous session's skill after `loadConversation`/`resetConversation` cleared it. **Closed by 16-04** — the guard `if (params.request_id === state.activeSessionId)` is correct: the backend's `_event_to_notification` sets `request_id = getattr(event, "session_id", "")` and `SkillLoadedEvent(session_id=session.id)`, so the comparison is a genuine session correlation. `addLoadedSkill` still dedups, and the clear-on-switch paths still hold.
**Remaining note (pre-existing, out of gap-closure scope):** `turn_started`, `token`, `response_complete`, `error`, and `cancelled` are NOT session-gated — a stale in-flight turn from a previous session could still append to the new session's conversation view after a mid-stream switch. Lower severity than WR-05 because the Scheduler runs one turn at a time and `switch_session` creates a fresh Agent, but worth a future hardening pass.

### WR-06: Unhandled promise rejections in InputBar chains can terminate the TUI (OPEN — untouched by gap-closure)

**File:** `tui-ink/src/app.tsx:56-63, 97`
**Issue:** The `/new` chain and `client.submitPrompt(trimmed).then(refreshSessions)` have no `.catch`. Node ≥15 defaults to `--unhandled-rejections=throw`, terminating the TUI process on a backend error. The `/skill` branch correctly has a `.catch`; its siblings don't. Pre-existing.
**Fix:**
```ts
client.submitPrompt(trimmed).then(refreshSessions).catch((err: Error) => {
  useAgentStore.getState().addError(err.message)
})
```

## Info

### IN-01: Degenerate ternary in `completeAssistantMessage` — FIXED (16-04)

**File:** `tui-ink/src/store/agent-store.ts:120`
**Issue:** `status: content ? "idle" : "idle"` replaced with a plain `status: "idle"` (verified in the diff; comment at line 120 documents the removal). Closed.

### IN-02: `SkillLoadStatus` documents a status the backend never returns (OPEN)

**File:** `tui-ink/src/types.ts:9`
**Issue:** `"not_found"` is never returned in a successful `skills.load` result — unknown skills come back as JSON-RPC error -32001. **Fix:** Drop `"not_found"` from the type (or wire it to the WR-01 code-carrying contract).

### IN-03: `EventPayload` discriminated union is dead code (OPEN)

**File:** `tui-ink/src/types.ts:71-79` (dependent: `tui-ink/src/bridge/rpc-client.ts:189-196, 199-296`)
**Issue:** The union is exported but never used for narrowing; the `handleEvent` switch is untyped with no `default` branch — a new backend event type is silently dropped. **Fix:** Type the switch against `EventPayload` with a `never` default, or add a `default` that logs unknown types.

### IN-04: `_write_json` local re-import + `default=str` masks serialization bugs (OPEN)

**File:** `backend/rpc/server.py:135-140`
**Issue:** Local `from dataclasses import asdict, is_dataclass` re-import; `json.dumps(data, default=str)` silently stringifies non-serializable values. **Fix:** Drop the local import and `default=str`.

### IN-05: No validation of the `jsonrpc` protocol version (OPEN)

**File:** `backend/rpc/server.py:298-303`
**Issue:** `raw.get("jsonrpc", "2.0")` accepts any value; a `"jsonrpc": "1.0"` request is processed as 2.0. **Fix:** Validate `raw.get("jsonrpc") == "2.0"` and respond `-32600` otherwise.

### IN-06: Mid-turn `/skill` chip timing caveat — documented in SUMMARY, not in code

**File:** `tui-ink/src/bridge/rpc-client.ts:284-294` (chip set), `tui-ink/src/app.tsx:66-95` (mid-turn branch)
**Issue:** Loading a skill mid-turn lights the chip immediately; the in-flight model may not see the body until the next turn (context snapshot). Not a bug — 16-04 SUMMARY documents this as the intended "safe via scan fix" semantics. **Fix (optional):** a code comment at the `skill_loaded` handler or the `/skill` branch noting the next-turn visibility, so the semantics survive future refactors.

---

_Reviewed: 2026-08-04T00:00:00Z_
_Reviewer: OpenCode (gsd-code-reviewer)_
_Depth: standard_
