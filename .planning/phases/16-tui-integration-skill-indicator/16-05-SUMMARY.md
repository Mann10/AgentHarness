---
phase: 16-tui-integration-skill-indicator
plan: 05
subsystem: ui
tags: [ink, string-width, footer-chip, truncation, wr-04, display-columns]

# Dependency graph
requires:
  - phase: 16-tui-integration-skill-indicator
    provides: skill-loaded footer chip + formatChip (16-03), WR-04 gap flagged in 16-VERIFICATION.md
provides:
  - Honest chip width budget: W = columns - CHIP_PADDING_X*2 - stringWidth(CHIP_LABEL + " ") — the fit check accounts for the full rendered row (padding + label + names), closing WR-04
  - Display-column measurement via string-width@8.2.2 (transitive Ink dep, no new direct dependency) for all fit comparisons — multibyte CJK/emoji skill names no longer undercounted
affects: [16-tui-integration-skill-indicator, 17-allowed-tools-enforcement-hardening]

# Tech tracking
tech-stack:
  added: [string-width@8.2.2 used directly in tui-ink/src/components/footer.tsx (already a transitive dep of ink@7.1.0 — NOT added to package.json; bundled by tsup)]
  patterns:
    - "Width-budget math reserves every rendered row element (paddingX*2 + label + text) before measuring content"
    - "All fit comparisons use string-width display columns instead of UTF-16 .length"

key-files:
  created: []
  modified:
    - tui-ink/src/components/footer.tsx

key-decisions:
  - "WR-04 fix: chip fit budget is W = columns - CHIP_PADDING_X*2 - stringWidth(CHIP_LABEL + ' ') — the old W = columns - 4 omitted the 7-cell label + 2-cell padding, letting a 'passing' chip wrap to a second line"
  - "string-width is used directly but NOT added to package.json — it is an existing transitive dep of ink@7.1.0 (resolved 8.2.2, ships index.d.ts) and tsup bundles it since only react + ink are external"

patterns-established:
  - "formatChip preserves UI-SPEC §6.1 drop-tail truncation and §9 hard floor byte-identically — only the budget and measurement changed"

requirements-completed: [ACT-06]

# Metrics
duration: 11min
completed: 2026-08-04
---

# Phase 16 Plan 05: Gap Closure (WR-04) — Honest Chip Width Budget Summary

**formatChip in the footer chip now budgets the full rendered row (padding + "Skill: " label + names) and measures every fit check in string-width display columns, so a chip that passes the fit check always renders on one line — closing WR-04 from 16-VERIFICATION.md**

## Performance

- **Duration:** 11 min
- **Started:** 2026-08-04T21:39:04Z
- **Completed:** 2026-08-04T21:50:11Z
- **Tasks:** 1
- **Files modified:** 1

## Accomplishments

- Rewrote `formatChip` budget from `W = columns - 4` to `W = columns - CHIP_PADDING_X*2 - stringWidth(CHIP_LABEL + " ")` — the old budget accounted only for chip-text padding, so a "fitting" chip (e.g. `demo-greeter · other` at 25 cols) actually rendered 27 cells of row width and wrapped to a second line. The new budget reserves the 2 padding cells + 7 label cells before the names, so a passing chip always fits the terminal row (WR-04 closed).
- Replaced all three `.length` budget comparisons with `stringWidth(...)` — UTF-16 code units undercount multibyte names (verified: `技能演示 · demo` is 11 code units but 15 display columns). CJK/emoji skill names now measured at true rendered width.
- Preserved UI-SPEC §6.1/§9 semantics exactly: drop-tail truncation with `+N more` dim suffix (N = dropped count, never hidden), `null` below the hard floor → caller hides the whole chip row. Constants (`CHIP_LABEL`/`CHIP_SEPARATOR`/`CHIP_MORE_SUFFIX`/`CHIP_PADDING_X`) and the chip + hint JSX are byte-identical.
- The `useAgentStore((s) => s.loadedSkills)` subscription and `useWindowSize` columns source are untouched — data flow unchanged (D-09).
- Functional spot check (node + real string-width@8.2.2): the WR-04 repro case that previously wrapped now hides cleanly; short-name rows fit on one line; CJK names measured at display width; narrow-terminal hard floor intact.

## task Commits

Each task was committed atomically:

1. **task 1: Honest chip width budget with string-width display-column measurement** - `7aecda1` (fix)

**Plan metadata:** `docs(16-05)` (final commit — this SUMMARY + state updates)

## Files Created/Modified

- `tui-ink/src/components/footer.tsx` - `formatChip` width budget now includes `CHIP_PADDING_X*2` + `stringWidth(CHIP_LABEL + " ")` and all fit checks use `stringWidth(...)` instead of `.length`; added `import stringWidth from "string-width"` (transitive ink dep, bundled by tsup)

## Decisions Made

- **WR-04 budget fix:** reserve the full rendered row — `paddingX*2` (2 cells) + `"Skill: "` label (7 cells) — before measuring the names. A chip passing the fit check can no longer wrap.
- **string-width used directly without a package.json entry:** it is an existing transitive dependency of ink@7.1.0 (resolved `string-width@8.2.2`, ships its own `index.d.ts`); tsup externalizes only react + ink, so the module resolves at build time. Not adding it keeps the dependency surface unchanged (matches review note).

## Deviations from Plan

None - plan executed exactly as written. (One comment reword during verification to satisfy the `grep -c "string-width"` returns-1 acceptance criterion — the literal `string-width` text was removed from a code comment so only the import line matches; no functional change.)

## Issues Encountered

- Git commit message quoting on Windows PowerShell: embedded `"` characters in the message body caused git to misinterpret the message as pathspecs. Resolved by writing the commit message to a temp file and committing with `git commit -F`. No code impact.

## User Setup Required

None - no external service configuration required.

## Next Phase Readiness

- WR-04 (chip width budget omits label) is closed with actionable evidence: grep gates pass (string-width import x1, stringWidth >= 4 usages, `columns - 4` x0, `.length <= W` x0), typecheck exits 0, tsup build succeeds, and a node spot-check confirms one-line-or-hide behavior at narrow widths.
- Phase 16 remaining: 16-04 (CR-01 stream-safety + WR-05 session correlation + human E2E checkpoint) is the only unexecuted plan; 16-05's narrow-terminal spot check can be folded into 16-04 task 3 E2E as the plan notes.
- Onward to Phase 17 (allowed-tools Enforcement & Hardening) after 16-04 completes.

## Self-Check: PASSED

- SUMMARY.md exists: `.planning/phases/16-tui-integration-skill-indicator/16-05-SUMMARY.md`
- Task commit exists: `7aecda1` (fix(16-05))
- Modified file exists: `tui-ink/src/components/footer.tsx`

---
*Phase: 16-tui-integration-skill-indicator*
*Completed: 2026-08-04*
