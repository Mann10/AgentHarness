---
phase: 260804-wgb
plan: 01
subsystem: ui
tags: [ink, tui, react, message-card, truecolor]

# Dependency graph
requires:
  - phase: 16-tui-integration-skill-indicator
    provides: live color/token vocabulary (16-UI-SPEC), notice tones, /skill notice flow, StreamingText component
  - phase: 09-ts-tui-json-rpc
    provides: base design system color vocabulary (09-UI-SPEC)
  - phase: 11-session-popup-and-panel-layout
    provides: message/notice rendering patterns (11-UI-SPEC)
provides:
  - Full-width bordered role sub-panels for every message (user/assistant/notice/error) with label-only header rows
  - Role-colored named-ANSI borders with truecolor-aware dark hex background tints and border-color-only fallback
  - Inter-card 1-cell gap in the reversed conversation column
affects: [16-tui-integration-skill-indicator, future TUI visual phases]

# Tech tracking
tech-stack:
  added: []  # no new dependencies (Ink ^7.1.0 Box props only)
  patterns:
    - "CARD_(BORDER|TINT|LABELS)[message.role] static record lookup — per-role styling without theme.ts (11-UI-SPEC §10)"
    - "HAS_TRUECOLOR module-load detection (COLORTERM + process.stdout.hasColors in try/catch) gating hex backgrounds"

key-files:
  created: []
  modified:
    - tui-ink/src/components/message.tsx
    - tui-ink/src/panels/conversation-panel.tsx

key-decisions:
  - "Direction B — full-width bordered cards per role (NOT chat bubbles, NOT two-column), per locked D-01"
  - "Label-only header rows (You/Assistant/Notice/Error), no timestamps, per locked D-02"
  - "All four roles get cards (user/assistant/notice/error), per locked D-03"
  - "Dark hex tints (user=#332a00, assistant=#002a1f, notice/error=#2a2a2a) applied only when HAS_TRUECOLOR; named-ANSI borders carry role identity in the no-truecolor fallback, per locked D-04"
  - "StreamingText untouched and kept inside the assistant card body (blinking ▊ cursor preserved), per locked D-05"

patterns-established:
  - "Role → card: single MessageCard wrapper (bordered Box) delegating to renderLabel + renderContent helpers"
  - "Truecolor detection: module-level `supportsTruecolor()` with try/catch default-false (mitigates T-260804-wgb-01)"

requirements-completed: []  # quick-260804-wgb — pending task-3 human verification before marking complete

# Metrics
duration: 8min
completed: 2026-08-04
---

# Phase [260804-wgb] Plan [01]: Redesign conversation panel with distinct bordered sub-panels — Summary

**MessageCard restructured into full-width bordered role sub-panels (label-only header row, role-colored named-ANSI border, truecolor-gated dark hex tint) with a 1-cell inter-card gap added to the reversed conversation column — code complete, awaiting task-3 human visual verification**

## Performance

- **Duration:** ~8 min (code tasks 1–2)
- **Started:** 2026-08-04T23:27:23Z
- **Completed (code):** 2026-08-04T23:30:00Z (task 3 checkpoint pending)
- **Tasks:** 2/3 complete (1 auto, 1 auto, 1 checkpoint:human-verify — NOT completed)
- **Files modified:** 2

## Accomplishments
- `MessageCard` renders every role (user/assistant/notice/error) as its own full-width single-bordered card with a label-only header row (`You` / `Assistant` / `Notice` / `Error`) — Direction B, no timestamps, no chat bubbles, no two-column layout.
- Role-colored named-ANSI borders (`CARD_BORDER`: yellow/green/gray/red) with dark hex background tints (`CARD_TINT`) applied only when `HAS_TRUECOLOR`; terminals without truecolor get border-color-only cards (background omitted).
- Streaming, notice tones (✓/✗), truncated indicator, and ✗ error glyph preserved verbatim inside the card body; `StreamingText` untouched (D-05).
- Reversed conversation column in `ConversationPanel` gained `gap={1}` so adjacent cards never render a `┘┌` seam.

## Task Commits

Each task was committed atomically:

1. **task 1: Restructure MessageCard into bordered role sub-panels** - `8c53157` (feat)
2. **task 2: Add inter-card spacing in the conversation column** - `f0d59b3` (feat)
3. **task 3: Human visual verification of sub-panel redesign** - PENDING (checkpoint:human-verify, blocking)

**Plan metadata:** `b9c1b10` (docs: plan conversation panel sub-panel redesign — prior commit)

## Files Created/Modified
- `tui-ink/src/components/message.tsx` - Rewritten `MessageCard`: single bordered card wrapper (`flexDirection="column"`, `borderStyle="single"`, `borderColor={CARD_BORDER[role]}`, `backgroundColor={HAS_TRUECOLOR ? CARD_TINT[role] : undefined}`, `paddingX={1}`) with `renderLabel` (header row) + `renderContent` (existing per-role rendering moved verbatim into the body). Added `CARD_LABELS`, `CARD_BORDER`, `CARD_TINT` records and `supportsTruecolor()`/`HAS_TRUECOLOR` module constants.
- `tui-ink/src/panels/conversation-panel.tsx` - Added `gap={1}` to the reversed conversation column (line 32). Single-prop change; reversal logic, outer border, header, status lines, empty state, and message mapping untouched.

## Decisions Made
- Followed the plan's locked decisions exactly (D-01..D-05) — no new decisions required during execution. Role identity is carried by named-ANSI borders (not hex) so the no-truecolor fallback keeps role colors.

## Deviations from Plan

None - plan executed exactly as written.

---

**Total deviations:** 0 auto-fixed
**Impact on plan:** N/A — no deviations.

## Issues Encountered
- None. `npm run typecheck` passed after task 1; `npm run typecheck` + `npm run build` both passed after task 2 in `tui-ink/`.

## User Setup Required

None - no external service configuration required. Human verification (task 3) requires the existing backend + TUI launch setup (same as prior Phase 16 E2E checks).

## Next Phase Readiness
- Code complete for the sub-panel redesign; `8c53157` + `f0d59b3` are on `feature/TUI_User_AI_Message_Distinction`.
- **Blocking:** task 3 human visual verification must be approved (or issues reported) before `quick-260804-wgb` can be marked complete. Verification steps are provided in the checkpoint message (below).

## Task 3 Human Verification Steps

Backend + TUI must be running (same setup used for prior Phase 16 E2E checks). Run `npm run dev` (watch build) in `tui-ink/` and `npm start` in a second terminal, or the project's usual TUI launch command. Then:

1. Send a message (e.g. "hi") and confirm the **user message renders as a full-width card** with a yellow border, `You` label row, and content below the label. Expected (colors omitted in ASCII):
   ```
   ┌──────────────────────────┐
   │ You                      │
   │ hi                       │
   └──────────────────────────┘
   ```
2. While the model replies, confirm the **assistant message renders as a green-bordered card** with `Assistant` label row, `▸` prefix, and the **blinking green ▊ cursor inside the card body** (D-05). After completion the cursor disappears and the full reply stays inside the card.
3. Type `/skill demo-greeter` and confirm a **notice card** appears: gray border, `Notice` label (dim), content `✓ Loaded skill demo-greeter` in green bold.
4. Type `/skill nope` and confirm a **notice card with error tone**: `✗ Skill 'nope' not found` in red bold.
5. Confirm cards are **full-width, stacked with a 1-cell gap** (no `┘┌` seam), auto-anchored to the latest message, and that the `● thinking` indicator + `Conversation · {title}` header + footer chip/hints are unchanged.
6. Confirm the window-resize and `Tab` panel-focus behaviors still work (borders stay aligned, no layout break at 60-col width).

Resume signal: type "approved" or describe the specific issue(s).

---
*Phase: 260804-wgb*
*Completed: 2026-08-04 (code tasks; task-3 verification pending)*

## Self-Check: PASSED

- FOUND: tui-ink/src/components/message.tsx
- FOUND: tui-ink/src/panels/conversation-panel.tsx
- FOUND: .planning/quick/260804-wgb-redesign-conversation-panel-with-distinc/260804-wgb-SUMMARY.md
- FOUND: commit `8c53157` (task 1)
- FOUND: commit `f0d59b3` (task 2)
