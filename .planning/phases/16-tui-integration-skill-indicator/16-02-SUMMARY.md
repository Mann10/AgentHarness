---
phase: 16-tui-integration-skill-indicator
plan: 02
subsystem: ui
tags: [skill-command, input-intercept, anchored-regex, ink, rpc, zustand, addSkillNotice]

# Dependency graph
requires:
  - phase: 16-01-tui-integration-skill-indicator
    provides: addSkillNotice store action + loadSkill() client method + SkillLoadResult contract + skill_loaded notification
  - phase: 15-session-behavior-skill-command
    provides: skills.load RPC + {skill, status} ack contract (adapter.py SKILL_NOT_FOUND message shape)
provides:
  - InputBar /skill intercept (bare usage + named loadSkill + outcome notices) — never forwarded to submitPrompt
  - SKILL_CMD anchored-regex gate (never matches /skills; startsWith forbidden)
  - D-04 verbatim not-found copy + SKILL_LOAD_FAILED wrapper for other RPC failures
affects: [16-03-tui-indicator-chip]

# Tech tracking
tech-stack:
  added: []
  patterns:
    - Slash-command intercept, never fall-through (D-05) — anchored regex gate instead of startsWith (research Pitfall 6)
    - Module-local const convention for copy strings (UI-SPEC §10 — no theme.ts)

key-files:
  created: []
  modified:
    - tui-ink/src/app.tsx

key-decisions:
  - "Branch gate is the anchored regex test SKILL_CMD.test(trimmed) (^/skill(?:\s+(.+))?$) — /skills fails both the end-anchor and the \s+ alternative and falls through to submitPrompt (Pitfall 6)"
  - "D-04 SKILL_NOT_FOUND surfaces the BARE verbatim copy `Skill '<name>' not found` — message-equality against the backend (adapter.py:107); SKILL_LOAD_FAILED wrapper reserved for every other failure (INVALID_PARAMS, INTERNAL_ERROR, cap refusal)"
  - "All /skill outcomes route through addSkillNotice(text, tone?) — NEVER addError (sets status:error, flips header red, Pitfall 5); no busy flag during load; chip not updated from this ack (notification-driven per 16-01, 16-03 owns the chip)"

patterns-established:
  - "Anchored-regex slash-command gate: /^\/cmd(?:\s+(.+))?$/ rejects prefix-colliding commands (/skills) by construction while still matching bare and named forms"
  - "Outcome-notice dispatch from one RPC promise: status-based success/info notices from result.skill (canonical name), message-equality error branch, wrapper fallback"

requirements-completed: [ACT-06]

# Metrics
duration: 5min
completed: 2026-08-03
---

# Phase 16 Plan 2: InputBar /skill Intercept Summary

**`/skill` intercept wired into the Ink InputBar: bare `/skill` shows the `Usage: /skill <name>` info notice and is never forwarded, `/skill <name>` routes through `client.loadSkill(name)` to success/info/error notices via `addSkillNotice` (canonical name from the RPC ack, D-04 bare not-found copy, `SKILL_LOAD_FAILED` wrapper for other failures), and the whole branch is gated on the anchored regex `SKILL_CMD.test(trimmed)` so `/skills` fails the test and falls through to `submitPrompt` exactly like any other text — the final `else` is the only path to the chat pipeline (D-05).**

## Performance

- **Duration:** 5 min
- **Started:** 2026-08-03T21:31:00Z (resumed mid-flight — previous executor cancelled)
- **Completed:** 2026-08-03T21:36:44Z
- **Tasks:** 1
- **Files modified:** 1

## Accomplishments

- `SKILL_USAGE_LINE`, `SKILL_CMD` (anchored `^\/skill(?:\s+(.+))?$`), and `SKILL_LOAD_FAILED` module-local constants added above `InputBar` (UI-SPEC §10 — no theme.ts exists)
- `/skill` branch inserted between `/sessions` and the final `else` in the `key.return` chain: bare → `addSkillNotice(SKILL_USAGE_LINE)` (never forwarded, D-05); named → `client.loadSkill(name)` → `Loaded skill <canonical>` (success) / `Skill '<canonical>' already loaded` (info) / `Skill '<name>' not found` (error, D-04 verbatim, no trailing period) / `Failed to load skill: {message}` (error, all other RPC failures)
- Branch gate is `SKILL_CMD.test(trimmed)` — a `startsWith` gate is forbidden (Pitfall 6) and asserted absent by grep; `submitPrompt` appears exactly once in the file (only the final `else`)
- All notices go through `addSkillNotice` (5 call sites); `addError` count in app.tsx is 0 — the header can never flip red on a failed slash command (Pitfall 5)
- No `busy` flag during the load (UI-SPEC §6.2 — input stays usable); chip not updated from this ack (16-01 notification contract drives the chip, rendered in 16-03)

## Task Commits

Each task was committed atomically:

1. **Task 1: InputBar /skill intercept — bare usage + named loadSkill + outcome notices** - `bf1d1df` (feat)
2. **Task 1 follow-up: reword /skill branch comment to satisfy submitPrompt grep gate** - `dbfbb9a` (fix)

**Plan metadata:** `(pending — committed after SUMMARY creation)`

## Files Created/Modified

- `tui-ink/src/app.tsx` - `SKILL_*` constants (lines 28-31) + `/skill` branch (lines 67-96) in `InputBar`'s `useInput` `key.return` chain: regex-gated intercept calling `client.loadSkill(name)` with status/message-based `addSkillNotice` outcome notices; `setInput("")`/`return` flows through unchanged so the input clears and focus is retained; only the final `else` reaches `submitPrompt`

## Decisions Made

- **Anchored regex as the branch gate, not `startsWith`** — `SKILL_CMD.test(trimmed)` is the gate itself; `/skills` fails the test (the trailing `s` breaks both the end-anchor and the `\s+` alternative) and falls through to `submitPrompt`. This is the T-16-05 mitigation (tampering) from the plan's threat model.
- **Canonical name from the ack, typed name only for not_found** — success/already_loaded notices render `result.skill` (the RPC ack's canonical name, UI-SPEC §6.3); the only typed-name echo is the D-04 not_found copy, which is exactly the backend's own message string (adapter.py:107) re-rendered with `tone:"error"`.
- **No `addError`, no `busy`, no chip update** — notices use `addSkillNotice` (never touches status/busy/error — T-16-07); the load doesn't set `busy`; the chip is fed only by the 16-01 `skill_loaded` notification (16-03 renders it).

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 1 - Bug] Comment contained literal `submitPrompt`, breaking the `grep -c "submitPrompt" == 1` acceptance gate**
- **Found during:** post-commit self-check (re-ran all 10 acceptance grep gates)
- **Issue:** The plan's own verbatim comment text (`falls through to the final else → submitPrompt`) contained the literal token, so `rg -c "submitPrompt"` returned 2 instead of the required 1. The criterion's intent — only the final `else` calls `client.submitPrompt` — was already satisfied (single call site at line 98); the extra match was comment prose.
- **Fix:** Reworded the comment to `falls through to the final else → chat prompt dispatch` — preserves the Pitfall 6 meaning (anchored regex gate, NOT startsWith) without the literal token.
- **Files modified:** tui-ink/src/app.tsx
- **Verification:** All 10 grep gates re-run — `submitPrompt` count now 1; typecheck exits 0
- **Committed in:** dbfbb9a (follow-up fix commit, no behavior change)

---

**Total deviations:** 1 auto-fixed (1 bug)
**Impact on plan:** Comment-only wording fix required to satisfy the plan's literal grep acceptance criterion; zero behavior change, no scope creep.

## Issues Encountered

- The previous executor attempt was cancelled mid-flight with an uncommitted modification to `tui-ink/src/app.tsx` implementing task 1. Verification confirmed it fully satisfied the plan's acceptance criteria (all 10 grep gates + `npm run typecheck` exit 0), so it was committed without rewrite.
- Pre-existing out-of-scope dirty state (`.gitignore`, `.opencode/opencode.json`, `mcp-servers/`) was left untouched — already logged in `deferred-items.md` by 16-01.

## User Setup Required

None - no external service configuration required.

## Next Phase Readiness

- **16-03 (Footer chip + notice rendering):** ready — `loadedSkills` store state and `Message.tone` were shipped in 16-01; the `/skill` InputBar branch (this plan) now produces the notices; 16-03 renders the chip from the notification and the tone variants in message.tsx, and hosts the blocking human E2E round-trip checkpoint
- **Verification note:** human E2E of the intercept (`/skill demo-greeter` notice + chip, bare `/skill` usage, `/skills` fall-through) runs in 16-03's blocking checkpoint per the plan's `<verification>` spec

---

*Phase: 16-tui-integration-skill-indicator*
*Completed: 2026-08-03*

## Self-Check: PASSED

- [x] `16-02-SUMMARY.md` exists on disk
- [x] Commit `bf1d1df` (feat: /skill intercept) exists in git history
- [x] Commit `dbfbb9a` (fix: comment reword) exists in git history
- [x] Grep gate G1: `SKILL_CMD` anchored regex present (count 1)
- [x] Grep gate G2: `SKILL_USAGE_LINE` present (count 2)
- [x] Grep gate G3: `SKILL_LOAD_FAILED` present (count 3)
- [x] Grep gate G4: bare `Skill '${name}' not found` copy present (count 2)
- [x] Grep gate G5: branch gated on `SKILL_CMD.test(trimmed)` (count 1)
- [x] Grep gate G6: `trimmed.startsWith` absent (count 0)
- [x] Grep gate G7: `client.loadSkill(name)` present (count 1)
- [x] Grep gate G8: `addSkillNotice` >= 5 call sites (count 5)
- [x] Grep gate G9: `addError` absent from app.tsx (count 0)
- [x] Grep gate G10: `submitPrompt` count == 1 (only the final else)
- [x] `npm run typecheck` — 0 errors
- [x] `npm run build` — tsup dist emits
- [x] `graphify update .` — 1034 nodes, 2272 edges, 56 communities
