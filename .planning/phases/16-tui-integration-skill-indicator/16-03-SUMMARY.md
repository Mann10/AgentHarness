---
phase: 16-tui-integration-skill-indicator
plan: 03
subsystem: ui
tags: [footer-chip, skill-indicator, notice-tones, truncation, ink, useWindowSize, zustand]

# Dependency graph
requires:
  - phase: 16-01-tui-integration-skill-indicator
    provides: loadedSkills store state + Message.tone + addLoadedSkill (chip data source, notification-driven)
  - phase: 16-02-tui-input-skill
    provides: /skill InputBar intercept + addSkillNotice outcome notices (the ack path feeding tone rendering)
provides:
  - Persistent footer chip row above the hint row (dim Skill: label + bold white names, ' · ' join, drop-tail truncation with dim +N more, hidden when empty / below floor)
  - /skill notice tone rendering (✓ green bold success / ✗ red bold error / dim italic info) with module-local glyph constants
affects: [17-allowed-tools-enforcement]

# Tech tracking
tech-stack:
  added: []
  patterns:
    - Module-local const convention for UI copy + glyphs (UI-SPEC §10 — no theme.ts)
    - Pure module-local truncation helper (formatChip) with hard floor (UI-SPEC §6.1/§9)
    - Subscriber-scoped store subscription (useAgentStore loadedSkills — re-renders on chip changes only)

key-files:
  created: []
  modified:
    - tui-ink/src/components/footer.tsx
    - tui-ink/src/components/message.tsx

key-decisions:
  - "Chip truncation is a pure drop-tail algorithm (formatChip): W = columns - 4; if joined names fit → render all, else drop trailing names until kept + ' · +N more' fits; below the ~18-col hard floor return null and hide the row (UI-SPEC §6.1/§9)"
  - "Chip renders ONLY from loadedSkills store state — the store subscription is the sole data source (D-09 live-events-only, zero inference, zero-chrome when empty); hint row preserved verbatim below it"
  - "Notice tones discriminate on message.tone in the notice branch: success = ✓ green bold, error = ✗ red bold, undefined = existing dim italic (fallback keeps 'Cancelled'/already_loaded/Usage unchanged); error role branch untouched"
  - "Glyph constants NOTICE_OK / NOTICE_ERR are module-local in message.tsx (UI-SPEC §10); no accent colors extended to the chip (UI-SPEC §5)"

patterns-established:
  - "Footer composition: flexDirection=column root with conditional chip row above the fixed hint row — zero-chrome when loadedSkills is empty (D-09)"
  - "Presentation-only task boundary: message.tsx controls rendering only; copy strings flow verbatim from 16-02's addSkillNotice calls (UI-SPEC §11)"

requirements-completed: [ACT-06]

# Metrics
duration: 12min
completed: 2026-08-03
---

# Phase 16 Plan 3: Skill Indicator UI Summary

**Persistent footer chip row (dim `Skill:` label + bold-white names joined ` · ` with drop-tail `+N more` truncation, hidden when no skills are loaded) above the untouched hint row, driven solely by the `loadedSkills` store state, plus `/skill` outcome notice tones (`✓` green bold success / `✗` red bold error / dim italic info fallback) in message.tsx — the human-approved E2E proves the full keystroke → JSON-RPC → load → notification → indicator round trip with zero stream pollution.**

## Performance

- **Duration:** 12 min
- **Started:** 2026-08-03T21:41:00Z
- **Completed:** 2026-08-03T21:53:53Z
- **Tasks:** 3 (2 code, 1 blocking human E2E checkpoint — approved)
- **Files modified:** 2

## Accomplishments

- `Footer` restructured to a `flexDirection="column"` root: the chip row renders ABOVE the hint row only when `loadedSkills.length > 0` — dim `Skill:` label, bold white names joined with ` · `, never wrapping (D-01/D-02/D-03/D-09)
- `formatChip` pure truncation helper implements UI-SPEC §6.1 exactly: `W = columns - 4`, full render when it fits, otherwise drop trailing names until `kept + " · +N more"` fits (dim suffix), and a hard floor that hides the row entirely below ~18 cols (§9) — locked by module-local `CHIP_LABEL`/`CHIP_SEPARATOR`/`CHIP_MORE_SUFFIX`/`CHIP_PADDING_X` constants (§10)
- `MessageCard` notice branch now discriminates on `message.tone`: `"success"` → `NOTICE_OK (✓)` green bold, `"error"` → `NOTICE_ERR (✗)` red bold, undefined → existing dim italic (fallback preserves the "Cancelled" notice and info tones verbatim); `error` role branch untouched (D-04, UI-SPEC §6.3)
- Blocking human E2E (task 3) approved by the user: `/skill demo-greeter` → `✓ Loaded skill` green notice + `Skill: demo-greeter` chip with no assistant message, second skill joins the chip in load order, dedup shows a dim info notice with no chip change, `/skill nope` is a red notice with a normal header, bare `/skill` shows usage, `/skills` falls through to chat, model-driven `read_skill` adds the chip with zero stream pollution, `/new` clears the chip, and narrow-terminal truncation shows `+N more` (ROADMAP criterion 4)
- All task acceptance grep gates pass (verified post-approval), `npm run typecheck` exits 0, `npm run build` emits dist

## Task Commits

Each task was committed atomically:

1. **Task 1: Footer chip row — dedicated line above hints with locked truncation** - `bf224e9` (feat)
2. **Task 2: Notice tone rendering — ✓ green bold / ✗ red bold / dim italic info** - `0e5fbc5` (feat)
3. **Task 3: Phase 16 end-to-end human verification (blocking checkpoint)** - no commit (human approval; verified via 1-2)

**Plan metadata:** `(pending — committed after SUMMARY creation)`

## Files Created/Modified

- `tui-ink/src/components/footer.tsx` - Footer restructured to column root: `useWindowSize` import (Ink 7.1), `useAgentStore((s) => s.loadedSkills)` subscription, module-local chip constants (`CHIP_LABEL`, `CHIP_SEPARATOR`, `CHIP_MORE_SUFFIX`, `CHIP_PADDING_X`), pure `formatChip` truncation helper (drop-tail + hard floor), conditional chip row above the verbatim hint row
- `tui-ink/src/components/message.tsx` - Module-local `NOTICE_OK`/`NOTICE_ERR` glyph constants; notice branch discriminates `message.tone` (success → green bold ✓, error → red bold ✗, undefined → dim italic fallback); error role branch untouched

## Decisions Made

- **Drop-tail truncation with a hard floor, not wrap or ellipsis** — names are dropped one at a time keeping the `+N more` count (never misleading about hidden skills); below ~18 cols the whole row hides per §9 (matches plan's locked UI-SPEC §6.1 algorithm).
- **Chip fed exclusively by the store, not the RPC ack** — `loadedSkills` is the only data source (notification-driven per 16-01/D-09); the chip never depends on `/skill` ack ordering and the notice never depends on the notification (T-16-10 mitigated).
- **Module-local constants instead of a theme.ts** — consistent with UI-SPEC §10 and the 16-02 precedent; no accent/cyan/blue extended to the chip (UI-SPEC §5).
- **Presentation-only task** — message.tsx renders whatever content `addSkillNotice` supplied verbatim (UI-SPEC §11); the file has no copy logic of its own.

## Deviations from Plan

None - plan executed exactly as written. (The plan's acceptance grep gates for tasks 1-2 were re-verified after the checkpoint approval: all pass; no Rule 1-4 deviations triggered.)

## Issues Encountered

None - all grep gates, typecheck, build, and the blocking human E2E passed on first verification pass.

## User Setup Required

None - no external service configuration required.

## Next Phase Readiness

- **Phase 17 (allowed-tools Enforcement & Hardening):** ready — Phase 16 is the final TUI indicator plan; ACT-06 (skill_loaded notification + visible indicator round trip, no stream pollution) is now fully complete across all five touchpoints with human E2E approval. Phase 17 owns the milestone E2E script (17-03) which can now assert the chip appears for `/skill` and `read_skill` loads and clears on `/new`.
- **Milestone close:** Phase 16 complete — all 3 plans (01 notification contract, 02 InputBar intercept, 03 indicator UI) delivered; the milestone E2E in 17-03 will exercise the full author → manifest → load → inject → JSONL-untouched → filter → indicator chain.
- **No blockers or concerns.**

---

*Phase: 16-tui-integration-skill-indicator*
*Completed: 2026-08-03*

## Self-Check: PASSED

- [x] `16-03-SUMMARY.md` exists on disk
- [x] Commit `bf224e9` (task 1: footer chip row) exists in git history
- [x] Commit `0e5fbc5` (task 2: notice tones) exists in git history
- [x] `tui-ink/src/components/footer.tsx` exists on disk — all 8 task-1 grep gates verified by file inspection
- [x] `tui-ink/src/components/message.tsx` exists on disk — all 5 task-2 grep gates verified by file inspection
- [x] `npm run typecheck` — 0 errors (exit 0)
- [x] `npm run build` — tsup dist emits (33.33 KB)
- [x] Task 3 blocking human E2E — approved by user (10-step checklist)
- [x] Working tree clean of plan changes (only pre-existing out-of-scope dirty state, logged in deferred-items.md)
