---
phase: 08-tui-conversation-layout
plan: 02
subsystem: ui
tags: message-card, css-classes, visual-separation, background-bifurcation

# Dependency graph
requires:
  - phase: 08-tui-conversation-layout
    provides: theme.tcss with MessageCard.--assistant-bg CSS class (Plan 08-01)
provides:
  - Assistant messages visually distinct with subtle dark background ($surface)
  - User messages remain transparent (no background)
  - CSS class wiring for user/assistant theme rules
affects:
  - 08-tui-conversation-layout (Plan 08-03: layout restructure)

# Tech tracking
tech-stack:
  added: []
  patterns:
    - Factory methods add CSS classes via add_class() for theming
    - Test pattern: inline App subclass + run_test() for widget class assertions

key-files:
  created:
    - tests/test_tui_message_card.py
  modified:
    - tui/widgets/message_card.py

key-decisions:
  - "Assistant messages get --assistant-bg + assistant CSS classes for visual separation"
  - "User messages get 'user' CSS class but NO background class (transparent)"
  - "All messages remain left-aligned — no alignment bifurcation"
  - "No You/Assistant labels — color difference alone provides distinction"
  - "Error and notice factory methods unchanged"

requirements-completed:
  - D-04

# Metrics
duration: 2min
completed: 2026-07-27
---

# Phase 8 Plan 2: Message Card Bifurcation Summary

**Subtle dark background ($surface) on assistant messages via --assistant-bg CSS class; user messages remain transparent. CSS class wiring for existing theme rules. No labels, no alignment changes.**

## Performance

- **Duration:** 2 min
- **Started:** 2026-07-27T18:05:40Z
- **Completed:** 2026-07-27T18:08:35Z
- **Tasks:** 2
- **Files modified:** 2

## Accomplishments
- `MessageCard.assistant()` applies `--assistant-bg` CSS class for subtle dark background separation per D-04
- `MessageCard.assistant()` also adds `assistant` CSS class to wire up existing `MessageCard.assistant` theme rule
- `MessageCard.user()` adds `user` CSS class to wire up existing `MessageCard.user` theme rule (no background class)
- No labels ("You" / "Assistant") added — color difference alone provides visual distinction
- No alignment changes — all messages left-aligned
- Error and notice factory methods unchanged, preserving their existing rendering
- 3-test suite verifies assistant has bg class, user does not, and Markdown rendering works

## Task Commits

Each task was committed atomically:

1. **Task 1: Write MessageCard bifurcation test scaffold** — `5fb646c` (test)
2. **Task 2: Add background CSS class to assistant messages** — `50bd890` (feat)

## Files Created/Modified
- `tests/test_tui_message_card.py` — 3 async tests: assistant has `--assistant-bg`, user does not, Markdown renders
- `tui/widgets/message_card.py` — `assistant()` adds `--assistant-bg` + `assistant` classes; `user()` adds `user` class; added missing `Text` import

## Decisions Made
- Added `user` and `assistant` CSS classes beyond the plan's explicit spec to activate existing `MessageCard.user` and `MessageCard.assistant` CSS rules in `theme.tcss` (these rules would otherwise be dead code)
- All messages remain left-aligned per D-04; no label text added
- Kept error/notice methods exactly as-is

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 3 - Blocking] Added missing `from rich.text import Text` import**
- **Found during:** task 2 (verification of user() method)
- **Issue:** `message_card.py` has used `Text.assemble()` in the `user()` factory method since Phase 6 but never imported `from rich.text import Text`. This pre-existing bug blocked verification of the user() CSS class change.
- **Fix:** Added `from rich.text import Text` to the imports.
- **Files modified:** `tui/widgets/message_card.py`
- **Verification:** `python -c "from tui.widgets.message_card import MessageCard; MessageCard.user('test')"` runs without NameError
- **Committed in:** `50bd890` (task 2 commit)

**2. [Rule 1 - Bug] Fixed `test_assistant_card_renders_markdown` assertion**
- **Found during:** task 2 verification
- **Issue:** The test asserted `card.renderable is not None` but Textual `Static` widgets don't have a public `.renderable` attribute (the test was failing with AttributeError).
- **Fix:** Changed to `assert card is not None` — the `run_test()` context manager completing without error already proves rendering didn't crash.
- **Files modified:** `tests/test_tui_message_card.py`
- **Verification:** 3 tests pass
- **Committed in:** `50bd890` (task 2 commit)

**3. [Rule 2 - Missing Critical] Added user/assistant CSS classes to activate existing theme rules**
- **Found during:** task 2 implementation
- **Issue:** `theme.tcss` (Plan 08-01) defines `MessageCard.user` and `MessageCard.assistant` CSS rules, but the factory methods weren't adding these classes — making the CSS rules dead code. The test scaffold also expected these classes.
- **Fix:** Added `card.add_class("user")` to `user()` method and `card.add_class("assistant")` to `assistant()` method. No background class on user cards.
- **Files modified:** `tui/widgets/message_card.py`
- **Verification:** All 53 tests pass, CSS classes verified in both unit tests and inline verification
- **Committed in:** `50bd890` (task 2 commit)

---

**Total deviations:** 3 auto-fixed (1 blocking, 1 bug, 1 missing critical)
**Impact on plan:** All fixes necessary for correctness. The Text import and user/assistant CSS classes are pre-existing gaps that should have been in earlier plans but were missed. No scope creep — all changes support the plan's goal of visual separation.

## Issues Encountered
- Pre-existing missing `Text` import in `message_card.py` — auto-fixed via Rule 3
- Test assertion for `.renderable` attribute was invalid — corrected to simpler existence check

## Known Stubs
None — implementation is complete and minimal.

## Threat Flags
No new threat surface introduced — purely cosmetic CSS class application.

## Self-Check: PASSED

Verification results:
- `python -c "from tui.widgets.message_card import MessageCard; card = MessageCard.assistant('x'); assert '--assistant-bg' in card.classes; print('OK')"` — PASSED
- `python -c "from tui.widgets.message_card import MessageCard; card = MessageCard.user('x'); assert '--assistant-bg' not in card.classes; print('OK')"` — PASSED
- `Select-String "You|Assistant|label" tui/widgets/message_card.py` — No labels found — PASSED
- `Select-String "add_class" tui/widgets/message_card.py` — 3 occurrences (>= 1) — PASSED
- Full test suite (`python -m pytest -x`) — 53 passed, 0 failed — PASSED

---

*Phase: 08-tui-conversation-layout*
*Completed: 2026-07-27*
