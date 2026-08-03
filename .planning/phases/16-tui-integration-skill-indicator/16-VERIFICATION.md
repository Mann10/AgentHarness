---
phase: 16-tui-integration-skill-indicator
verified: 2026-08-03T22:40:00Z
status: gaps_found
score: 3/4 must-haves verified
overrides_applied: 0
gaps:
  - truth: "The indicator never pollutes the assistant message stream (ROADMAP SC-4) — the /skill notice path can permanently strand the in-flight streaming assistant message"
    status: failed
    reason: "CR-01 from the phase's own code review (16-REVIEW.md, committed as e4060d3 — the last commit, no fix followed) is live in the code. When the user runs `/skill <name>` while a response is streaming, the RPC ack resolves and `addSkillNotice` appends a notice while the last conversation entry is the streaming assistant message. The next `token` event sees `lastMsg.role !== \"assistant\"` and calls `startAssistantMessage()`, spawning a SECOND assistant box; the original message keeps `isStreaming: true` forever. Permanent UI corruption (stuck ▸ spinner box, turn content split across two boxes) — reachable in the phase's primary use case (loading a skill during an active conversation)."
    artifacts:
      - path: "tui-ink/src/bridge/rpc-client.ts"
        issue: "token handler (236-246) checks only the last conversation entry for a streaming assistant; a notice inserted by /skill mid-stream makes it spawn a new assistant box instead of appending"
      - path: "tui-ink/src/store/agent-store.ts"
        issue: "addSkillNotice (188-194) appends to conversation without truncating/handling a trailing streaming assistant message"
      - path: "tui-ink/src/app.tsx"
        issue: "`busy` destructured at line 34 but never referenced (WR-03) — the /skill branch is not gated on busy, which is the enabler for CR-01"
    missing:
      - "Fix CR-01: in the token handler, scan the conversation backwards for the last assistant message with isStreaming and append to it; only call startAssistantMessage() when none exists (reviewer-suggested fix), OR gate the /skill branch on busy (WR-03) so mid-turn loads are refused/deferred"
      - "Re-run a human E2E step covering `/skill <name>` DURING a streaming response (not covered by the approved 10-step checkpoint)"
  - truth: "TUI chip width budget fits the terminal (16-03 artifact quality)"
    status: partial
    reason: "WR-04 (review): `W = columns - 4` budgets only the chip text but the rendered row also carries CHIP_LABEL ('Skill: ' — 7 cells) plus paddingX=1 (2 cells). A chip passing the fit check can still wrap to a second line, and the budget is measured in UTF-16 code units not display columns."
    artifacts:
      - path: "tui-ink/src/components/footer.tsx"
        issue: "formatChip (14-24) width budget omits label + padding; no string-width measurement"
    missing:
      - "Include CHIP_LABEL and padding in the budget; measure display width (string-width) instead of .length"
  - truth: "skill_loaded notification applied to the active session only"
    status: partial
    reason: "WR-05 (review): the skill_loaded case reads only payload.skill and ignores request_id (the backend session id). A notification already in flight when the user switches sessions arrives after loadConversation clears loadedSkills and re-adds a skill belonging to the previous session."
    artifacts:
      - path: "tui-ink/src/bridge/rpc-client.ts"
        issue: "skill_loaded case (281-288) sets the chip unconditionally; no session correlation"
    missing:
      - "Guard on request_id === activeSessionId before addLoadedSkill"
human_verification: []
---

# Phase 16: TUI Integration (Skill Indicator) Verification Report

**Phase Goal:** The TUI surfaces skill activity: `/skill <name>` works from the input bar and a visible "Skill loaded" indicator appears whenever a skill loads — driven by a typed `skill_loaded` notification, never by inference or stream pollution.
**Verified:** 2026-08-03T22:40:00Z
**Status:** gaps_found
**Re-verification:** No — initial verification

## Goal Achievement

### Observable Truths

| #   | Truth | Status     | Evidence       |
| --- | ----- | ---------- | -------------- |
| 1   | SC-1: User can type `/skill <name>` in the TUI input bar and the skill loads via the backend RPC — intercepted like `/session`/`/new`, never forwarded as a chat prompt | ✓ VERIFIED | `tui-ink/src/app.tsx:67-96` — `SKILL_CMD` anchored regex gate (`^\/skill(?:\s+(.+))?$`, line 30), branch gated on `SKILL_CMD.test(trimmed)` (not startsWith), bare `/skill` → usage notice, named → `client.loadSkill(name)` → `addSkillNotice` outcomes; `submitPrompt` reachable only from the final else (grep count 1); `addError` count 0; typecheck + build pass |
| 2   | SC-2: TUI shows a visible "Skill loaded" indicator whenever a skill loads — model-driven (`read_skill`) or via `/skill` | ✓ VERIFIED | `footer.tsx:26-54` — chip row above hint row, dim `Skill:` label + bold white names joined ` · `, hidden when `loadedSkills.length === 0`; `message.tsx:46-72` — notice tones (✓ green bold / ✗ red bold / dim italic); driven by `loadedSkills` store state only (D-09). Blocking human E2E (10-step) approved by the user during execution |
| 3   | SC-3: The indicator round-trips end-to-end through the typed `skill_loaded` notification: keystroke → JSON-RPC → load → notification → indicator (all five touchpoints) | ✓ VERIFIED | `test_skills_load_rpc_round_trip_emits_notification` passes (independent response + notification channels); backend emission at `runtime.py:217` strictly after `add_skill_message`; server mapping `EVENT_SKILL_LOADED: NotificationType.skill_loaded.value` (server.py:63) + `{skill}`-only extractor (server.py:113-115); `NotificationType.skill_loaded` 8th member (protocol.py:87); subscribe/unsubscribe (server.py:177, 194); TUI `case "skill_loaded"` → `store.addLoadedSkill(p.skill)` only (rpc-client.ts:281-288) |
| 4   | SC-4: The indicator never pollutes the assistant message stream — no fake tool cards, no streamed text chunks, no token/tool_result smuggling | ✗ FAILED | The `skill_loaded` notification path itself is clean (chip-only, no notice, no status/busy). BUT CR-01 (phase's own review, unfixed): the inline-notice indicator path (`/skill` ack → `addSkillNotice`) inserted mid-stream strands the in-flight streaming assistant message — the next token spawns a second assistant box and the original never finalizes. This is stream corruption from the phase's indicator mechanism. See gap below |

**Score:** 3/4 truths verified

### Required Artifacts

| Artifact | Expected | Status | Details |
| -------- | -------- | ------ | ------- |
| `harness/events.py` | SkillLoadedEvent dataclass + EVENT_SKILL_LOADED | ✓ VERIFIED | Lines 63-73, 92 — dataclass (session_id + skill), constant `"SkillLoadedEvent"` |
| `harness/runtime.py` | Emission in load_skill after add_skill_message | ✓ VERIFIED | Line 217 — publish between add_skill_message (213) and return (218); zero events on already_loaded (196), KeyError (193), cap refusal (205-208) |
| `harness/__init__.py` | Barrel export | ✓ VERIFIED | Import block (17, 26) + `__all__` (57, 66) |
| `backend/rpc/protocol.py` | NotificationType.skill_loaded (8th member) | ✓ VERIFIED | Line 87 |
| `backend/rpc/server.py` | Mapping + extractor + subscribe/unsubscribe | ✓ VERIFIED | Mapping (63), `_extract_skill_loaded_payload` returning `{"skill": event.skill}` (113-115), extractor registration (131), subscribe (177), unsubscribe (194) |
| `tui-ink/src/types.ts` | SkillLoadedPayload + EventPayload member + Message.tone + AgentState.loadedSkills | ✓ VERIFIED | Lines 67-68, 79, 100, 115 |
| `tui-ink/src/store/agent-store.ts` | loadedSkills state + addLoadedSkill + addSkillNotice + reset in both paths | ✓ VERIFIED | Init (59), dedup-append addLoadedSkill (181-186), addSkillNotice never touches status/busy/error (188-194), resetConversation (222) + loadConversation (237) both reset |
| `tui-ink/src/bridge/rpc-client.ts` | handleEvent skill_loaded case → addLoadedSkill only | ✓ VERIFIED | Lines 281-288 — chip state only, no notice/status/busy. Caveat: WR-05 session correlation absent |
| `tui-ink/src/app.tsx` | InputBar /skill intercept (bare + named) | ✓ VERIFIED | Lines 28-31 constants, 67-96 branch, regex-gated; caveat WR-03: busy never used |
| `tui-ink/src/components/footer.tsx` | Chip row above hints, truncation, hidden when empty | ✓ VERIFIED | Lines 1-55; caveat WR-04 width budget omits label |
| `tui-ink/src/components/message.tsx` | Notice tone rendering | ✓ VERIFIED | Lines 46-72, NOTICE_OK/NOTICE_ERR constants |
| `tests/test_skill_loaded_notification.py` | 9 tests, all five automated ACT-06 dimensions | ✓ VERIFIED | 9 `def test_` — emits both paths, no_event x3, wire_format x2, round_trip, pollution; **9 passed** |

### Key Link Verification

| From | To | Via | Status | Details |
| ---- | --- | --- | ------ | ------- |
| `harness/runtime.py` | `harness/events.py` | `await self._event_bus.publish(SkillLoadedEvent(session_id=session.id, skill=info.name))` | WIRED | runtime.py:217, strictly after add_skill_message |
| `backend/rpc/server.py` | `harness/events.py` | EVENT_SKILL_LOADED subscribe/unsubscribe + mapping | WIRED | server.py:177, 194, 63, 131 |
| `backend/rpc/server.py` | `backend/rpc/protocol.py` | `EVENT_SKILL_LOADED: NotificationType.skill_loaded.value` + `_extract_skill_loaded_payload` returns `{"skill": ...}` only | WIRED | server.py:63, 113-115; D-06 enforced |
| `tui-ink/src/bridge/rpc-client.ts` | `tui-ink/src/store/agent-store.ts` | `case "skill_loaded"` → `store.addLoadedSkill(p.skill)` and nothing else | WIRED | rpc-client.ts:281-288 |
| `tui-ink/src/app.tsx` | `tui-ink/src/bridge/rpc-client.ts` | `client.loadSkill(name)` → `request("skills.load")` | WIRED | app.tsx:76 |
| `tui-ink/src/app.tsx` | `tui-ink/src/store/agent-store.ts` | `addSkillNotice(text, tone)` for outcome notices; never addError | WIRED | app.tsx:74, 80, 81, 91, 93 |
| `tui-ink/src/app.tsx` | `client.submitPrompt` | Final `else` is the only path; /skill branch returns before it | WIRED | app.tsx:98; grep count 1 |
| `tui-ink/src/components/footer.tsx` | `tui-ink/src/store/agent-store.ts` | `useAgentStore((s) => s.loadedSkills)` subscription | WIRED | footer.tsx:27 |
| `tui-ink/src/components/message.tsx` | `tui-ink/src/types.ts` | `message.tone` discriminated in notice branch | WIRED | message.tsx:47-64 |

### Data-Flow Trace (Level 4)

| Artifact | Data Variable | Source | Produces Real Data | Status |
| -------- | ------------- | ------ | ------------------ | ------ |
| footer chip | `loadedSkills` | `skill_loaded` notification → `addLoadedSkill` → store state | ✓ FLOWING | Round-trip test asserts `{"skill": "demo-greeter"}` payload; human E2E (approved) confirmed chip appears from `/skill` and `read_skill`; `/new` clears it |
| notice tones | `message.tone` | `addSkillNotice(text, tone)` call sites in app.tsx /skill branch | ✓ FLOWING | Tone set only by whitelisted call sites; message.tsx renders per locked UI-SPEC §6.3 table |

### Behavioral Spot-Checks

| Behavior | Command | Result | Status |
| -------- | ------- | ------ | ------ |
| All 9 notification tests pass | `python -m pytest tests/test_skill_loaded_notification.py -q` | 9 passed | ✓ PASS |
| No regressions | `python -m pytest -q` | 191 passed, 1 skipped | ✓ PASS |
| TUI typecheck | `npm run typecheck` (tui-ink) | 0 errors | ✓ PASS |
| TUI build | `npm run build` (tui-ink) | tsup dist 33.33 KB | ✓ PASS |
| Blocking human E2E (10-step round trip) | Manual (task 3 of 16-03) | Approved by user per execution record and task note | ✓ PASS (note: did NOT cover `/skill` during a streaming response — CR-01 trigger) |

### Requirements Coverage

| Requirement | Source Plan | Description | Status | Evidence |
| ----------- | ----------- | ----------- | ------ | -------- |
| ACT-06 | 16-01, 16-02, 16-03 (all `requirements: [ACT-06]`) | TUI shows a visible indicator when a skill is loaded | ✓ SATISFIED (caveat: CR-01) | Chip + notices exist and round-trip through the typed notification (verified above). Requirement literally met, but the phase's headline /skill flow can corrupt the conversation view when used mid-stream — the indicator mechanism is not fully safe in all reachable states. Phase gate should NOT proceed until CR-01 is fixed |

**Orphaned requirements:** None. REQUIREMENTS.md maps ACT-06 → Phase 16 only; all three plans declare ACT-06; no unclaimed IDs for this phase (CAP-02/CAP-04 belong to Phase 17).

### Anti-Patterns Found

| File | Line | Pattern | Severity | Impact |
| ---- | ---- | ------- | -------- | ------ |
| tui-ink/src/bridge/rpc-client.ts | 236-246 | token handler spawns new assistant box when last message is a notice (CR-01) | 🛑 Blocker | /skill during streaming → permanent second ▸ spinner box; turn content split; unrecoverable |
| tui-ink/src/app.tsx | 34 | `busy` destructured, never referenced (WR-03) | ⚠️ Warning | /skill not gated on busy — enables CR-01; mid-turn load may never be seen by in-flight model |
| tui-ink/src/bridge/rpc-client.ts | 180 | JSON-RPC error code discarded; verbatim-string match in app.tsx:90 (WR-01) | ⚠️ Warning | Backend message rewording silently converts D-04 bare copy into generic wrapper |
| tui-ink/src/store/agent-store.ts | 131-146, 148-171 | tool_call_id dropped; results matched by tool name (WR-02) | ⚠️ Warning | Two read_skill calls in one turn → first result overwritten by second |
| tui-ink/src/components/footer.tsx | 14-24 | chip width budget omits label + padding (WR-04) | ⚠️ Warning | Chip passes fit check yet wraps to a second line; multibyte names undercounted |
| tui-ink/src/bridge/rpc-client.ts | 281-288 | skill_loaded applied without session correlation (WR-05) | ⚠️ Warning | In-flight notification after session switch re-adds stale skill to chip |
| tui-ink/src/app.tsx | 57-64, 98 | unhandled promise rejections in /new + submitPrompt chains (WR-06) | ⚠️ Warning | Backend error terminates the TUI process (Node unhandled-rejections=throw) |
| (all files) | — | No TODO/FIXME/placeholder/stub patterns found | ℹ️ Info | grep scan clean |

### Human Verification Required

None outstanding — the blocking 10-step human E2E was approved by the user during execution.

**Caveat:** the approved E2E checklist (steps 1-10 of 16-03 task 3) never exercised `/skill <name>` **while a response is streaming** — which is exactly CR-01's trigger. After the CR-01 fix lands, a human re-check of that scenario is required (see gap).

### Gaps Summary

**Primary blocker (CR-01, from the phase's own code review — unfixed):** The `/skill` inline-notice indicator corrupts the assistant message stream when a skill is loaded during an active response. `addSkillNotice` inserts a notice after the streaming assistant message; the `token` handler (rpc-client.ts:241) then sees a non-assistant last message and starts a second assistant box, permanently stranding the original with `isStreaming: true`. This is the phase's headline use case (loading a skill mid-conversation) and produces irreversible UI corruption. The review (16-REVIEW.md, status `issues_found`, 1 critical + 6 warnings) was committed as the **last** commit (`e4060d3`); **no fix commit exists after it**.

**Secondary gaps (review warnings, all still open):** WR-03 (dead `busy` gate — the enabler for CR-01), WR-04 (chip width budget omits label), WR-05 (no session correlation on skill_loaded), plus WR-01/WR-02/WR-06 (pre-existing patterns adjacent to the phase's code, documented for the hardening pass).

**What is verified and solid:** The typed `skill_loaded` notification contract across all five touchpoints (backend emission → mapping/extractor → protocol → handleEvent → store), the `{skill}`-only payload (D-06), zero notifications on no-op loads (D-07), the `/skill` input intercept (never forwarded, `/skills` falls through), the footer chip + notice tones, the 9-test suite (all pass), full suite (191 passed, 1 skipped), typecheck + build clean, and the human-approved E2E round trip.

**Why this phase cannot be marked passed:** SC-4 ("The indicator never pollutes the assistant message stream") is violated by CR-01 — the phase's own review classified it critical, and the codebase evidence confirms it is live. Phase 16 must not proceed to Phase 17 with this defect open.

---

_Verified: 2026-08-03T22:40:00Z_
_Verifier: OpenCode (gsd-verifier)_
