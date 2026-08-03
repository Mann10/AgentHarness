---
phase: 16-tui-integration-skill-indicator
reviewed: 2026-08-03T00:00:00Z
depth: standard
files_reviewed: 12
files_reviewed_list:
  - backend/rpc/protocol.py
  - backend/rpc/server.py
  - harness/__init__.py
  - harness/events.py
  - harness/runtime.py
  - tests/test_skill_loaded_notification.py
  - tui-ink/src/app.tsx
  - tui-ink/src/bridge/rpc-client.ts
  - tui-ink/src/components/footer.tsx
  - tui-ink/src/components/message.tsx
  - tui-ink/src/store/agent-store.ts
  - tui-ink/src/types.ts
findings:
  critical: 1
  warning: 6
  info: 5
  total: 12
status: issues_found
---

# Phase 16: Code Review Report

**Reviewed:** 2026-08-03T00:00:00Z
**Depth:** standard
**Files Reviewed:** 12
**Status:** issues_found

## Summary

Reviewed the complete `skill_loaded` notification pipeline (harness event → RPC server mapping/extractor → wire notification → TUI handleEvent → zustand chip state), the `/skill` InputBar intercept with notice tones, and the footer chip row. Backend wiring is solid: the D-06 `{skill}`-only payload contract holds (`test_payload_is_skill_only` passes by construction), event emission correctly fires only after the body is in context, and `EventBus.publish` swallows subscriber exceptions so a failing stdout write cannot break `load_skill`. No injection/traversal/leak findings — `SkillStore.lookup/load` resolve only against discovered skill dirs, and `json.dumps` escapes embedded newlines so the NDJSON stream stays line-safe.

The dominant defect is on the TUI side: the `/skill` notice path can permanently strand the in-flight streaming assistant message (CR-01) — the phase's headline feature corrupts the conversation view whenever a skill is loaded mid-response. Secondary issues: the JSON-RPC error code is discarded forcing a fragile verbatim-string match, tool_call_id is dropped at add time forcing name-based result matching, the footer chip width budget ignores the label, and several promise chains can reject unhandled.

## Critical Issues

### CR-01: Skill notice added mid-stream strands the streaming assistant message

**File:** `tui-ink/src/bridge/rpc-client.ts:240-243` (trigger: `tui-ink/src/app.tsx:76-96`, `tui-ink/src/store/agent-store.ts:188-194`)
**Issue:** When the user runs `/skill <name>` while a response is streaming, the RPC response resolves and `addSkillNotice` appends a `notice` message to the conversation while the last entry is the streaming assistant message. The next `token` event then sees `lastMsg.role !== "assistant"` and calls `startAssistantMessage()`, spawning a *second* assistant box; all subsequent tokens and `response_complete`/`error`/`cancelled` apply to the new box (those handlers only inspect the last message). The original streaming message keeps `isStreaming: true` forever: the conversation permanently renders a second "▸" spinner box, the old box's `StreamingText` never finalizes, and the turn's completed content is split across two boxes. This is reachable in the phase's primary use case (loading a skill during an active conversation) and is permanent UI state corruption.
**Fix:** In the `token` handler, scan the conversation backwards for the last `assistant` message with `isStreaming` and append to it; only call `startAssistantMessage()` when none exists:
```ts
case "token": {
  const p = payload as { session_id: string; chunk: string; request_id: string }
  const state = useAgentStore.getState()
  const lastStreaming = [...state.conversation]
    .reverse()
    .find((m) => m.role === "assistant" && m.isStreaming)
  if (!lastStreaming) store.startAssistantMessage()
  store.appendToken(p.chunk)
  break
}
```
(Alternatively, `addSkillNotice` could truncate a trailing streaming message first, matching the `cancelled` path — but that loses the notice's interleaving and still drops the streaming box.)

## Warnings

### WR-01: JSON-RPC error code discarded — forces fragile verbatim-string equality

**File:** `tui-ink/src/bridge/rpc-client.ts:180` (dependent: `tui-ink/src/app.tsx:90`)
**Issue:** `pending.reject(new Error((msg.error as { message?: string }).message ?? "RPC error"))` throws away `msg.error.code` (-32001 SKILL_NOT_FOUND, -32603, etc.). app.tsx:90 then discriminates on `err.message === \`Skill '${name}' not found.\`` — an exact-match against backend copy (adapter.py:107). Any rewording of that message silently converts the D-04 bare-copy branch into the generic `SKILL_LOAD_FAILED` wrapper, and the code comments encode this coupling as if it were a contract. Two sources of truth (message text + code) are both needed; only one is transported.
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

### WR-02: tool_call_id dropped at add-time — tool results matched by tool *name*

**File:** `tui-ink/src/store/agent-store.ts:131-146, 148-171` (dependent: `tui-ink/src/bridge/rpc-client.ts:222, 233`)
**Issue:** `addToolCall(name, args, callId)` never stores the backend's `tool_call_id` (parameter unused). `updateToolResult`/`setToolCallError` then match `tc.name === callId || tc.id === callId`, and rpc-client.ts:233 passes `p.tool_name` as `callId`. When the same tool is invoked twice in one turn (e.g., two `read_skill` calls), every entry with that name is updated — the first call's result is overwritten with the second's, both get the same `duration`, and `tc.id === callId` can never match a backend id. Pre-existing, but in the reviewed files and the tool-monitor path adjacent to this phase's skill work.
**Fix:** Add a `callId?: string` field to `ToolCallStatus`, store `p.tool_call_id` in `addToolCall`, and match exclusively on it:
```ts
addToolCall: (name, args, callId) => set((s) => ({ toolCalls: [...s.toolCalls, { id: nextToolId(), name, args, callId: callId ?? undefined, status: "running", startedAt: now(), result: undefined, duration: undefined }] }))
updateToolResult: (callId, result) => set((s) => ({ toolCalls: s.toolCalls.map((tc) => tc.callId === callId ? { ...tc, status: "success" as const, result, duration: now() - tc.startedAt } : tc) }))
```

### WR-03: `/skill` intercept not gated on `busy`; the `busy` selector is dead

**File:** `tui-ink/src/app.tsx:34, 67-96`
**Issue:** `const { busy } = useAgentStore()` (line 34) is destructured but never referenced — the gate was clearly intended and dropped. The `/skill` branch therefore executes while a turn is in flight. Loading a skill mid-turn injects the system message into `session.context` after the running turn may have already snapshotted its context, so the in-flight model may never see the body — yet the `skill_loaded` notification unconditionally lights the chip, claiming the skill is loaded in the conversation. This is also the enabler of CR-01.
**Fix:** Either gate the branch (`if (busy) { store.addSkillNotice("Wait for the response to finish before loading a skill"); return }` — or auto-defer) or, if mid-turn loads are intended, drop the dead variable and document the mid-turn semantics; the chip claim then needs to be scoped to when the body actually enters the turn's context.

### WR-04: Footer chip width budget omits the "Skill: " label — "fitting" chips still overflow

**File:** `tui-ink/src/components/footer.tsx:14-24`
**Issue:** `const W = columns - 4` budgets only the chip text (2 cells padding each side), but the rendered row also contains `CHIP_LABEL` ("Skill: " — 7 cells) plus `paddingX={1}` (2 cells), i.e. ~9 cells beyond the chip text. A chip with `columns - 11 < length <= columns - 4` passes the fit check yet the row is `columns + 5` wide, so Ink wraps the chip onto a second line and breaks the footer layout. Additionally the budget is measured in UTF-16 code units (`joined.length`) while cells are display columns — any multibyte skill name (CJK/emoji) undercounts and overflows.
**Fix:** Include label and padding in the budget and measure display width:
```ts
import stringWidth from "string-width"   // already a transitive Ink dep
const W = columns - 4 - stringWidth(CHIP_LABEL)
const joined = names.join(CHIP_SEPARATOR)
if (stringWidth(joined) <= W) return joined
```

### WR-05: `skill_loaded` applied without session correlation

**File:** `tui-ink/src/bridge/rpc-client.ts:281-287`
**Issue:** The handler reads only `payload.skill`; the notification's `request_id` (the backend's session id, per `_event_to_notification`) is ignored and the chip is set unconditionally. `loadConversation` (session switch) and `resetConversation` (`/new`) clear `loadedSkills`, but a `skill_loaded` notification already in flight when the user switches sessions arrives *after* the clear and re-adds a skill belonging to the previous session — chip and active session then disagree (the new session's context does not contain the skill body). Narrow race, but chip accuracy is the phase's core feature.
**Fix:** Guard on the active session:
```ts
case "skill_loaded": {
  const p = payload as { skill: string }
  const state = useAgentStore.getState()
  if (params.request_id === state.activeSessionId) store.addLoadedSkill(p.skill)
  break
}
```

### WR-06: Unhandled promise rejections in InputBar chains can terminate the TUI

**File:** `tui-ink/src/app.tsx:57-64, 98`
**Issue:** The `/new` chain (`client.createSession().then(...).then(...)`) and `client.submitPrompt(trimmed).then(refreshSessions)` have no `.catch`. If the backend errors (e.g., the RPC process exited after connect — `stop()`/exit handling leaves `pending` rejected), the rejection is unhandled; Node ≥15 defaults to `--unhandled-rejections=throw`, which terminates the TUI process. The new `/skill` branch correctly has a `.catch`; its siblings don't. Pre-existing pattern, but in the reviewed file and adjacent to the new branch.
**Fix:** Route failures through the store, e.g.:
```ts
client.submitPrompt(trimmed).then(refreshSessions).catch((err: Error) => {
  useAgentStore.getState().addError(err.message)
})
```

## Info

### IN-01: Degenerate ternary in `completeAssistantMessage`

**File:** `tui-ink/src/store/agent-store.ts:117`
**Issue:** `status: content ? "idle" : "idle"` — both branches identical; the conditional is dead and the intent is unclear (an error state for empty content was likely meant). The caller (rpc-client response_complete) sets `idle` anyway.
**Fix:** `return { conversation: msgs, status: "idle" }`, or make the ternary meaningful (`content ? "idle" : "error"`) if empty content should be surfaced.

### IN-02: `SkillLoadStatus` documents a status the backend never returns

**File:** `tui-ink/src/types.ts:9`
**Issue:** `"not_found"` is part of `SkillLoadStatus`, but the backend never returns it in a successful `skills.load` result — unknown skills raise `KeyError` and come back as JSON-RPC error -32001 (adapter.py:106-107). app.tsx only branches on `loaded`/`already_loaded`; the third union member is misleading.
**Fix:** Drop `"not_found"` from the type (or carry it as the rejected-error contract if the RPC client ever surfaces codes — see WR-01).

### IN-03: `EventPayload` discriminated union is dead code

**File:** `tui-ink/src/types.ts:71-79` (dependent: `tui-ink/src/bridge/rpc-client.ts:189-196, 207-289`)
**Issue:** The union is exported but never used for narrowing — rpc-client casts `msg.params` to a raw shape and the `handleEvent` switch is untyped with no `default` branch. A new backend event type would be silently dropped with no compile error, and payload field renames wouldn't be caught.
**Fix:** Type the switch against `EventPayload` (exhaustive `switch` with `never` default), or at minimum add a `default` case that logs unknown types.

### IN-04: `_write_json` local re-import + `default=str` masks serialization bugs

**File:** `backend/rpc/server.py:135-140`
**Issue:** `from dataclasses import asdict, is_dataclass` re-imports inside the function while `asdict` is already imported at module top (line 15). More importantly, `json.dumps(data, default=str)` silently stringifies any non-JSON-serializable value — a dataclass in a payload would serialize as its `repr` instead of failing loudly, hiding contract violations.
**Fix:** Drop the local import and remove `default=str` (let `TypeError` surface in the event handler, where `EventBus.publish` logs it via `return_exceptions=True`).

### IN-05: No validation of the `jsonrpc` protocol version

**File:** `backend/rpc/server.py:298-303`
**Issue:** `raw.get("jsonrpc", "2.0")` accepts any value; a `"jsonrpc": "1.0"` request is processed as 2.0. Spec-compliance nit (JSON-RPC 2.0 requires rejecting non-2.0 with -32600).
**Fix:** Validate `raw.get("jsonrpc") == "2.0"` in the request-validation branch and respond with `INVALID_REQUEST` otherwise.

---

_Reviewed: 2026-08-03T00:00:00Z_
_Reviewer: OpenCode (gsd-code-reviewer)_
_Depth: standard_
