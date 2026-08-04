# Plan 07-01: Theme + Layout Foundation - Summary

**Status:** Complete

## Tasks

### Task 1: Write theme test scaffold
- Created `tests/test_tui_theme.py` with 3 tests:
  - `test_theme_registration` — verifies `claude-dark` theme is registered and active
  - `test_sidebar_not_in_layout` — verifies no `JobQueueSidebar` in DOM
  - `test_status_bar_not_in_layout` — verifies no `StatusBar` or `#tool-timeline` in DOM
- Added `StubRuntime` helper class for test isolation

### Task 2: Create theme.tcss and register Claude Code dark theme
- Created `tui/theme.tcss` (40+ lines) with Claude Code-inspired CSS variables
- Registered `claude-dark` `Theme` in `on_mount()` with warm dark palette
- Replaced inline `CSS` classvar with `CSS_PATH = "theme.tcss"`
- Removed Tokyo Night hex values from app.py

### Task 3: Restructure app.py layout
- Composed minimal layout: Header > ConversationView > Horizontal#bottom-bar(Static indicators + InputBar)
- Removed imports of `JobQueueSidebar`, `StatusBar`, `ToolTimeline`
- Stripped all StatusBar/ToolTimeline calls from event handlers
- Removed `on_screen_pop` (was StatusBar-only)
- Updated `tui/widgets/__init__.py` to drop `JobQueueSidebar`, `StatusBar` exports

## Verification
- ✅ `from tui.app import AgentHarnessTUI` — imports OK
- ✅ `from tui.widgets import ConversationView, InputBar, MessageCard` — exports OK
- ✅ No references to removed widgets in app.py
- ✅ No Tokyo Night hex values in app.py
