---
phase: 16-tui-integration-skill-indicator
verified: 2026-08-04T23:20:00Z
status: passed
score: 4/4 must-haves verified
overrides_applied: 0
re_verification:
  previous_status: gaps_found
  previous_score: 3/4
  gaps_closed:
    - "CR-01 stream-safety: /skill during a streaming response no longer strands the in-flight assistant message (SC-4 restored)"
    - "WR-04 honest chip width budget: full rendered row (label + padding) budgeted, display-column measurement via string-width"
    - "WR-05 session correlation: skill_loaded chip update gated on request_id === activeSessionId"
  gaps_remaining: []
  regressions: []
human_verification: []
---

# Phase 16: TUI Integration (Skill Indicator) Verification Report

**Phase Goal:** TUI Integration (Skill Indicator) — persistent footer chip showing loaded skills, inline notices for every `/skill` outcome, and a stream-safe indicator that never pollutes the assistant message stream.
**Verified:** 2026-08-04T23:20:00Z
**Status:** passed
**Re-verification:** Yes — all three gaps (CR-01, WR-04, WR-05) from the 2026-08-03 report are closed and verified against the codebase

## Goal Achievement

### Observable Truths

| #   | Truth   | Status     | Evidence       |
| --- | ------- | ---------- | -------------- |
| 1   | SC-1: User can type `/skill <name>` in the TUI input bar and the skill loads via the backend RPC — intercepted like `/session`/`/new`, never forwarded as a chat prompt | ✓ VERIFIED | `tui-ink/src/app.tsx:30` anchored `SKILL_CMD` regex, branch gated on `SKILL_CMD.test(trimmed)` (line 66, not startsWith), bare `/skill` → usage notice (72-73), named → `client.loadSkill(name)` (75), `submitPrompt` reachable only from the final else (line 97, grep count 1), `addError` count 0 |
| 2   | SC-2: TUI shows a visible "Skill loaded" indicator whenever a skill loads — model-driven (`read_skill`) or via `/skill` | ✓ VERIFIED | `footer.tsx:30-58` — chip row above hint row (dim `Skill:` label + bold white names joined ` · `, hidden when empty), driven by `loadedSkills` store state only; `message.tsx:47-64` — notice tones (✓ green bold / ✗ red bold / dim italic fallback). WR-04 now closed: budget accounts for the full rendered row (see below). Blocking human E2E (10-step) approved by user per 16-03 SUMMARY |
| 3   | SC-3: The indicator round-trips end-to-end through the typed `skill_loaded` notification: keystroke → JSON-RPC → load → notification → indicator (all five touchpoints) | ✓ VERIFIED | Backend emission at `harness/runtime.py:217` strictly after `add_skill_message`; `EVENT_SKILL_LOADED: NotificationType.skill_loaded.value` (server.py:63) + `{skill}`-only extractor (113-115); protocol 8th member (protocol.py:87); subscribe/unsubscribe (server.py:177, 194); TUI `case "skill_loaded"` (rpc-client.ts:284-294) → `store.addLoadedSkill(p.skill)`. WR-05 now closed: the case guards `params.request_id === state.activeSessionId` before mutating the chip (line 292). 9-test round-trip suite passes |
| 4   | SC-4: The indicator never pollutes the assistant message stream — no fake tool cards, no streamed text chunks, no token/tool_result smuggling | ✓ VERIFIED | CR-01 closed: `token` (rpc-client.ts:236-247) and `response_complete` (248-268) scan the conversation **backwards** for the last `assistant && isStreaming` message (`lastStreaming`), calling `startAssistantMessage()` only when none exists (line 244) — a mid-stream `/skill` notice can no longer spawn a second ▸ box or strand the original. Store actions target the same message via the shared `lastStreamingIdx` helper (agent-store.ts:51-56, used at 102/118/126); no `msgs[msgs.length - 1]` streaming targets remain. Dead `busy` destructure removed from app.tsx (WR-03). Human E2E 8-step mid-stream check **APPROVED** per 16-04 SUMMARY (8/8) |

**Score:** 4/4 truths verified

### Gap Closure Verification (re-verification focus)

| Gap (2026-08-03) | Closure Plan | Code Evidence | Status |
| ----------------- | ------------ | ------------- | ------ |
| CR-01 — mid-stream `/skill` notice strands the streaming assistant message | 16-04 (commits `40d12ed`, `b87cf52`) | Backwards scan in both streaming handlers (rpc-client.ts:241, 260); `lastStreamingIdx` helper + index-targeted store mutations (agent-store.ts:51-56, 102, 118, 126); `startAssistantMessage()` call count 1, inside the `!lastStreaming` guard only; dead `busy` destructure gone (app.tsx); human E2E 8-step approved | ✓ CLOSED |
| WR-04 — chip width budget omits label + padding; UTF-16 units | 16-05 (commit `7aecda1`) | `W = columns - CHIP_PADDING_X*2 - stringWidth(CHIP_LABEL + " ")` (footer.tsx:19) = full rendered row; all fit comparisons via `stringWidth` (21, 25); no `columns - 4`, no `.length <= W` | ✓ CLOSED |
| WR-05 — skill_loaded applied without session correlation | 16-04 (commit `40d12ed`) | `if (params.request_id === state.activeSessionId) store.addLoadedSkill(p.skill)` (rpc-client.ts:292); backend `_event_to_notification` sets `request_id = session_id` (verified in 16-REVIEW trace) | ✓ CLOSED |

### Required Artifacts

| Artifact | Expected | Status | Details |
| -------- | -------- | ------ | ------- |
| `harness/events.py` | SkillLoadedEvent dataclass + EVENT_SKILL_LOADED | ✓ VERIFIED | Lines 64-73, 92 |
| `harness/runtime.py` | Emission in load_skill after add_skill_message | ✓ VERIFIED | Line 217 — publish between add_skill_message (213) and return (218) |
| `harness/__init__.py` | Barrel export | ✓ VERIFIED | Import block (17, 26) + `__all__` (57, 66) |
| `backend/rpc/protocol.py` | NotificationType.skill_loaded (8th member) | ✓ VERIFIED | Line 87 |
| `backend/rpc/server.py` | Mapping + `{skill}`-only extractor + subscribe/unsubscribe | ✓ VERIFIED | Mapping (63), extractor returning `{"skill": event.skill}` (113-115), registration (131), subscribe (177), unsubscribe (194) |
| `tui-ink/src/types.ts` | SkillLoadedPayload + EventPayload member + Message.tone + AgentState.loadedSkills | ✓ VERIFIED | Lines 67, 79, 100, 115 |
| `tui-ink/src/store/agent-store.ts` | loadedSkills + addLoadedSkill + addSkillNotice + lastStreamingIdx-targeted streaming actions | ✓ VERIFIED | Init (70) + resetConversation (225) + loadConversation (240); addLoadedSkill dedup-append (184-189); addSkillNotice never touches status/busy/error (191-197); `lastStreamingIdx` helper (51-56) used by all three streaming mutations |
| `tui-ink/src/bridge/rpc-client.ts` | Backwards-scan token/response_complete + session-gated skill_loaded | ✓ VERIFIED | Lines 236-268, 284-294; `params.request_id === state.activeSessionId` (292) |
| `tui-ink/src/app.tsx` | InputBar /skill intercept + dead `busy` destructure removed | ✓ VERIFIED | Lines 28-31 constants, 66-95 branch, regex-gated; no `const { busy }`; `addError` count 0; `submitPrompt` count 1 |
| `tui-ink/src/components/footer.tsx` | Honest chip width budget (string-width display columns) | ✓ VERIFIED | Lines 1, 18-28 — `stringWidth` import, full-row budget, all fit checks display-column |
| `tui-ink/src/components/message.tsx` | Notice tone rendering | ✓ VERIFIED | Lines 5-6 (NOTICE_OK/NOTICE_ERR), 47-64 (tone branches), 67 (dim italic fallback) |
| `tests/test_skill_loaded_notification.py` | 9 tests, all five automated ACT-06 dimensions | ✓ VERIFIED | **9 passed** (re-run 2026-08-04) |

### Key Link Verification

| From | To | Via | Status | Details |
| ---- | --- | --- | ------ | ------- |
| `harness/runtime.py` | `harness/events.py` | `await self._event_bus.publish(SkillLoadedEvent(session_id=session.id, skill=info.name))` | WIRED | runtime.py:217, strictly after add_skill_message |
| `backend/rpc/server.py` | `harness/events.py` | EVENT_SKILL_LOADED subscribe/unsubscribe + mapping | WIRED | server.py:177, 194, 63, 131 |
| `backend/rpc/server.py` | `backend/rpc/protocol.py` | mapping + `{skill}`-only extractor (D-06) | WIRED | server.py:63, 113-115 |
| `tui-ink/src/bridge/rpc-client.ts` | `tui-ink/src/store/agent-store.ts` | `case "skill_loaded"` → session-gated `store.addLoadedSkill(p.skill)` and nothing else | WIRED | rpc-client.ts:284-294 |
| `tui-ink/src/bridge/rpc-client.ts` | `tui-ink/src/store/agent-store.ts` | `token`/`response_complete` handlers find `lastStreaming` by backwards scan → store actions target the same message via `lastStreamingIdx` | WIRED | rpc-client.ts:241, 260 ↔ agent-store.ts:102, 118 (same synchronous call stack — review-traced) |
| `tui-ink/src/app.tsx` | `tui-ink/src/bridge/rpc-client.ts` | `client.loadSkill(name)` → `request("skills.load")` | WIRED | app.tsx:75 |
| `tui-ink/src/app.tsx` | `tui-ink/src/store/agent-store.ts` | `addSkillNotice(text, tone)` for outcome notices; never addError | WIRED | app.tsx:73, 79, 80, 90, 92 |
| `tui-ink/src/app.tsx` | `client.submitPrompt` | Final `else` is the only path; /skill branch returns before it | WIRED | app.tsx:97; grep count 1 |
| `tui-ink/src/components/footer.tsx` | `tui-ink/src/store/agent-store.ts` | `useAgentStore((s) => s.loadedSkills)` subscription (unchanged by 16-05) | WIRED | footer.tsx:31 |
| `tui-ink/src/components/message.tsx` | `tui-ink/src/types.ts` | `message.tone` discriminated in notice branch | WIRED | message.tsx:47-64 |

### Data-Flow Trace (Level 4)

| Artifact | Data Variable | Source | Produces Real Data | Status |
| -------- | ------------- | ------ | ------------------ | ------ |
| footer chip | `loadedSkills` | `skill_loaded` notification (session-gated) → `addLoadedSkill` → store state | ✓ FLOWING | Round-trip test asserts `{"skill": "demo-greeter"}` payload; human E2E (approved) confirmed chip from `/skill` and `read_skill`; `/new` clears it (resetConversation:225, loadConversation:240) |
| notice tones | `message.tone` | `addSkillNotice(text, tone)` call sites in app.tsx /skill branch | ✓ FLOWING | Tone set only by whitelisted call sites; message.tsx renders per UI-SPEC §6.3 |
| streaming box | `conversation` (streaming assistant) | `token` events → `appendToken` at `lastStreamingIdx` | ✓ FLOWING | Mid-stream notices no longer redirect tokens (CR-01); human E2E verified single-box completion twice |

### Behavioral Spot-Checks

| Behavior | Command | Result | Status |
| -------- | ------- | ------ | ------ |
| All 9 notification tests pass | `python -m pytest tests/test_skill_loaded_notification.py -q` | 9 passed | ✓ PASS (re-run) |
| No regressions | `python -m pytest -q` | 192 passed, 1 skipped | ✓ PASS (re-run) |
| TUI typecheck | `npm run typecheck` (tui-ink) | 0 errors | ✓ PASS (re-run) |
| TUI build | `npm run build` (tui-ink) | tsup dist 44.57 KB | ✓ PASS (re-run) |
| Blocking human E2E (10-step round trip, 16-03 task 3) | Manual | Approved by user per 16-03 SUMMARY | ✓ PASS (recorded) |
| Blocking human E2E — `/skill` DURING streaming (16-04 task 3, CR-01 trigger) | Manual | Approved by user per 16-04 SUMMARY — 8/8 checks: no second ▸ box, single-box completion twice (two skills), clean cancel truncation, session-scoped `/new` reload | ✓ PASS (recorded) |

### Requirements Coverage

| Requirement | Source Plan | Description | Status | Evidence |
| ----------- | ---------- | ----------- | ------ | -------- |
| ACT-06 | 16-01, 16-02, 16-03, 16-04, 16-05 (all five plans declare `requirements: [ACT-06]`) | TUI shows a visible indicator when a skill is loaded | ✓ SATISFIED | Chip + notices exist, round-trip through the typed `skill_loaded` notification, stream-safe under mid-stream loads (CR-01 closed), session-scoped (WR-05 closed), honest width budget (WR-04 closed). All four ROADMAP success criteria verified |

**Orphaned requirements:** None. REQUIREMENTS.md maps ACT-06 → Phase 16 only (traceability table line 87); CAP-02/CAP-04 map to Phase 17 (lines 89, 91) and are not claimed by any Phase 16 plan. No unclaimed IDs for this phase.

### Anti-Patterns Found

| File | Line | Pattern | Severity | Impact |
| ---- | ---- | ------- | -------- | ------ |
| tui-ink/src/components/footer.tsx | 1 | `import stringWidth from "string-width"` not declared in `tui-ink/package.json` (transitive Ink dep only) — **new finding from 16-REVIEW** | ⚠️ Warning (non-blocking) | Resolves today via `string-width@8.2.2` in node_modules (verified: typecheck + build pass, 44.57 KB). Fragile: a future Ink release dropping/restructuring the transitive dep breaks `npm run build`/`typecheck` with module-not-found. **Recommendation:** declare `"string-width": "^8.2.0"` in `tui-ink/package.json` (matching the resolved version) during the Phase 17 hardening pass. Does not block the phase goal |
| tui-ink/src/bridge/rpc-client.ts | 180 | JSON-RPC error code discarded; verbatim-string match in app.tsx:89 (WR-01, pre-existing, untouched by gap closure) | ⚠️ Warning | Backend message rewording would silently convert the D-04 bare not_found copy into the generic wrapper. Works today (adapter.py:107 string is deterministic). Phase 17 hardening follow-up |
| tui-ink/src/store/agent-store.ts | 134-174 | tool_call_id dropped at add-time; results matched by tool name (WR-02, pre-existing, untouched) | ⚠️ Warning | Two read_skill calls in one turn → first result overwritten by second in the tool monitor. Cosmetic, pre-existing. Phase 17 hardening follow-up |
| tui-ink/src/app.tsx | 56-63, 97 | Unhandled promise rejections in `/new` + submitPrompt chains (WR-06, pre-existing, untouched) | ⚠️ Warning | Backend error could terminate the TUI (Node unhandled-rejections=throw). The `/skill` branch itself has `.catch` (82-94). Phase 17 hardening follow-up |
| (all files) | — | No TODO/FIXME/placeholder/stub patterns found | ℹ️ Info | grep scan clean |
| IN-02..IN-06 | — | `"not_found"` in SkillLoadStatus (dead value), untyped EventPayload union, `_write_json` `default=str`, no jsonrpc version validation, mid-turn chip timing caveat (documented) | ℹ️ Info | Pre-existing or documented design notes; Phase 17 hardening candidates |

### Human Verification Required

None outstanding — both blocking human E2E checkpoints are recorded as user-approved:

1. **10-step round trip** (16-03 task 3): `/skill demo-greeter` → notice + chip, second skill joins, dedup info notice, not_found red notice with normal header, bare usage, `/skills` falls through, model-driven `read_skill` with zero pollution, `/new` clears, narrow-terminal truncation — **approved** (16-03 SUMMARY).
2. **Mid-stream `/skill` during an active response** (16-04 task 3, the previously-missing CR-01 trigger): no second ▸ box, single-box completion (twice, two skills), no stranded spinner, clean cancel truncation, session-scoped `/new` reload — **approved 8/8** (16-04 SUMMARY, completed 2026-08-04T22:17:36Z).

### Gaps Summary

**No gaps remain.** All three items from the 2026-08-03 verification are closed with codebase evidence:

- **CR-01 (blocker) — CLOSED:** the token and response_complete handlers scan backwards for the last streaming assistant, and the store's `appendToken`/`completeAssistantMessage`/`truncateStreamingMessage` target that exact message via the shared `lastStreamingIdx` helper. A mid-stream `/skill` notice can no longer spawn a second assistant box or strand the original with `isStreaming: true`. Fix commits `40d12ed` + `b87cf52` land after the review commit `e4060d3`; the phase-gate human E2E (8-step, `/skill` during streaming) is approved; the latest review pass (bf86bcf) confirms the fix holds under trace.
- **WR-04 — CLOSED:** the chip width budget is `W = columns - CHIP_PADDING_X*2 - stringWidth(CHIP_LABEL + " ")` — the full rendered row — and all fit checks use display columns (`string-width@8.2.2`). Commit `7aecda1`. The review's residual finding (string-width not declared in package.json) is a non-blocking fragility warning with a concrete recommendation; the build is verified working today.
- **WR-05 — CLOSED:** `skill_loaded` guards `params.request_id === state.activeSessionId` before `addLoadedSkill`; the backend `request_id` is the session id, so the correlation is genuine (review-traced).

**Open review findings (WR-01, WR-02, WR-06, IN-02..IN-06) are pre-existing or informational, untouched by gap closure, and do not block the phase goal.** They are acceptable follow-ups for the Phase 17 hardening pass (allowed-tools enforcement). Per Step 9b, they are not deferred items — Phase 17's success criteria cover allowed-tools filtering and milestone E2E, not these TUI quality items — so they are recorded here as non-blocking recommendations, not gaps.

**Final verdict:** All four ROADMAP success criteria (SC-1..SC-4) verified, ACT-06 satisfied, 4/4 truths, no blockers, both required human E2E checkpoints approved. Phase 16 goal is achieved and the phase may proceed to Phase 17.

---

_Verified: 2026-08-04T23:20:00Z_
_Verifier: OpenCode (gsd-verifier)_
